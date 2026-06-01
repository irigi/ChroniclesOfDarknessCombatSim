use pyo3::prelude::*;
use pyo3::types::{PyDict, PyDictMethods, PyList, PyListMethods};

use crate::action::{encode_action, Action, ACTION_SPACE_SIZE};
use crate::character::{
    Attributes, ArmorProfile, BuildDefinition, CombatSkills, DamageType,
    SplatBuild, Splat, VampireDisciplines, WeaponProfile,
};
use crate::combat::{CombatState, MAX_TURNS};

// ─── Pure-Rust simulation environment (Send + Sync) ───────────────────────────

/// Internal simulation environment. Pure Rust — no PyO3 types. `Send` so it
/// can be stepped in parallel across threads by `VecEnv`.
pub struct SimEnv {
    pub builds: Vec<BuildDefinition>,
    pub teams: Vec<u8>,
    pub state: Option<CombatState>,
    seed_counter: u64,
    /// Team of the agent who "owns" this env slot (used for reward sign).
    pub agent_team: u8,
}

impl SimEnv {
    pub fn new(builds: Vec<BuildDefinition>, teams: Vec<u8>) -> Self {
        let agent_team = teams.first().copied().unwrap_or(0);
        Self {
            builds,
            teams,
            state: None,
            seed_counter: 0,
            agent_team,
        }
    }

    pub fn reset(&mut self, seed: Option<u64>) -> Vec<f32> {
        let s = seed.unwrap_or_else(|| {
            self.seed_counter = self.seed_counter.wrapping_add(1);
            self.seed_counter
        });
        let state = CombatState::new(self.builds.clone(), self.teams.clone(), s);
        let obs = state.encode_observation();
        self.state = Some(state);
        obs
    }

    /// Returns (obs, reward, terminated, truncated).
    pub fn step(&mut self, action: usize) -> (Vec<f32>, f32, bool, bool) {
        let state = match self.state.as_mut() {
            Some(s) => s,
            None => {
                // Not reset — return zeros
                let obs_len = self.builds.len() * OBS_PER_CHAR + GLOBAL_OBS;
                return (vec![0.0; obs_len], 0.0, true, false);
            }
        };

        let actor_team = state.characters[state.current_actor()].team;
        let (step_reward, terminated) = state.step(action);

        let terminal_reward = if terminated {
            state.terminal_reward(actor_team)
        } else {
            0.0
        };
        // Sign flip: reward is from actor's perspective, not agent_team
        let reward = step_reward + terminal_reward;

        let truncated = state.turn > MAX_TURNS;
        let obs = state.encode_observation();
        (obs, reward, terminated, truncated)
    }

    pub fn action_mask(&self) -> Vec<bool> {
        match &self.state {
            Some(s) => s.legal_mask(),
            None => {
                let mut mask = vec![false; ACTION_SPACE_SIZE];
                mask[encode_action(Action::Pass)] = true;
                mask
            }
        }
    }

    pub fn is_done(&self) -> bool {
        self.state.as_ref().map(|s| s.done).unwrap_or(false)
    }

    pub fn obs_size(&self) -> usize {
        self.builds.len() * OBS_PER_CHAR + GLOBAL_OBS
    }
}

/// Observation vector layout constants (must match encode_observation layout).
/// OBS_PER_CHAR = 30 (Phase 7: added power levels p4-p6, Wits, condition flags)
pub const OBS_PER_CHAR: usize = 30;
pub const GLOBAL_OBS: usize = 3;

// ─── Python-facing single environment ─────────────────────────────────────────

#[pyclass]
pub struct CombatEnv {
    inner: SimEnv,
}

#[pymethods]
impl CombatEnv {
    /// Create a new environment.
    ///
    /// `builds_json` — JSON list of BuildDefinition objects
    /// `teams`       — list of team indices (0 or 1) matching builds order
    #[new]
    pub fn new(builds_json: &str, teams: Vec<u8>) -> PyResult<Self> {
        let builds: Vec<BuildDefinition> = serde_json::from_str(builds_json)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        if builds.len() != teams.len() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "builds and teams must have the same length",
            ));
        }
        Ok(Self {
            inner: SimEnv::new(builds, teams),
        })
    }

    /// Reset and return (obs, info_dict).
    #[pyo3(signature = (seed=None))]
    fn reset(&mut self, py: Python<'_>, seed: Option<u64>) -> PyResult<(Vec<f32>, PyObject)> {
        let obs = self.inner.reset(seed);
        let info: PyObject = PyDict::new_bound(py).into_any().unbind();
        Ok((obs, info))
    }

    /// Step and return (obs, reward, terminated, truncated, info_dict).
    fn step(&mut self, py: Python<'_>, action: usize) -> PyResult<(Vec<f32>, f32, bool, bool, PyObject)> {
        let (obs, reward, terminated, truncated) = self.inner.step(action);
        let info: PyObject = PyDict::new_bound(py).into_any().unbind();
        Ok((obs, reward, terminated, truncated, info))
    }

    /// Legal action mask for the current state.
    fn action_mask(&self) -> Vec<bool> {
        self.inner.action_mask()
    }

    fn action_space_size(&self) -> usize {
        ACTION_SPACE_SIZE
    }

    fn obs_size(&self) -> usize {
        self.inner.obs_size()
    }

    fn current_actor_idx(&self) -> PyResult<usize> {
        self.inner.state.as_ref()
            .map(|s| s.current_actor())
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("call reset() first"))
    }

    fn is_done(&self) -> bool {
        self.inner.is_done()
    }

    /// Returns a summary dict for the UI / debugging.
    fn get_state_summary(&self, py: Python<'_>) -> PyResult<PyObject> {
        let state = self.inner.state.as_ref()
            .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("call reset() first"))?;
        let dict = PyDict::new_bound(py);
        dict.set_item("turn", state.turn)?;
        dict.set_item("done", state.done)?;
        dict.set_item("winner_team", state.winner_team.map(|t| t as i32))?;

        let chars_list = PyList::empty_bound(py);
        for (i, ch) in state.characters.iter().enumerate() {
            let ch_dict = PyDict::new_bound(py);
            ch_dict.set_item("build_id", ch.build_id)?;
            ch_dict.set_item("team", ch.team)?;
            ch_dict.set_item("name", &state.builds[i].name)?;
            ch_dict.set_item("bashing", ch.health.count(DamageType::Bashing))?;
            ch_dict.set_item("lethal", ch.health.count(DamageType::Lethal))?;
            ch_dict.set_item("aggravated", ch.health.count(DamageType::Aggravated))?;
            ch_dict.set_item("max_health", ch.health.size)?;
            ch_dict.set_item("willpower", ch.willpower)?;
            ch_dict.set_item("resource", ch.resource())?;
            ch_dict.set_item("is_incapacitated", ch.is_incapacitated)?;
            ch_dict.set_item("in_torpor", ch.in_torpor)?;
            ch_dict.set_item("initiative", ch.initiative)?;
            chars_list.append(ch_dict.into_any())?;
        }
        dict.set_item("characters", chars_list.into_any())?;
        Ok(dict.into_any().unbind())
    }
}

// ─── Build helper functions ───────────────────────────────────────────────────

#[pyfunction]
pub fn make_mortal_json(
    id: u32, name: &str,
    strength: u8, dexterity: u8, stamina: u8,
    intelligence: u8, wits: u8, resolve: u8,
    presence: u8, manipulation: u8, composure: u8,
    brawl: u8, weaponry: u8, firearms: u8, athletics: u8,
) -> PyResult<String> {
    let b = BuildDefinition {
        id, name: name.to_string(), splat: Splat::Mortal,
        attributes: Attributes::new(strength, dexterity, stamina, intelligence, wits, resolve, presence, manipulation, composure),
        skills: CombatSkills { brawl, weaponry, firearms, athletics, stealth: 0 },
        weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
        splat_data: SplatBuild::Mortal, size: 5,
        merits: std::collections::HashMap::new(),
    };
    serde_json::to_string(&b).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
pub fn make_vampire_json(
    id: u32, name: &str,
    strength: u8, dexterity: u8, stamina: u8,
    intelligence: u8, wits: u8, resolve: u8,
    presence: u8, manipulation: u8, composure: u8,
    brawl: u8, weaponry: u8, firearms: u8, athletics: u8,
    blood_potency: u8,
    celerity: u8, vigor: u8, resilience: u8,
) -> PyResult<String> {
    let vitae_max = crate::splats::vampire::vitae_max(blood_potency);
    let b = BuildDefinition {
        id, name: name.to_string(), splat: Splat::Vampire,
        attributes: Attributes::new(strength, dexterity, stamina, intelligence, wits, resolve, presence, manipulation, composure),
        skills: CombatSkills { brawl, weaponry, firearms, athletics, stealth: 0 },
        weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
        splat_data: SplatBuild::Vampire { blood_potency, vitae_max, disciplines: VampireDisciplines { celerity, vigor, resilience, ..Default::default() } },
        size: 5, merits: std::collections::HashMap::new(),
    };
    serde_json::to_string(&b).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
pub fn make_werewolf_json(
    id: u32, name: &str,
    strength: u8, dexterity: u8, stamina: u8,
    intelligence: u8, wits: u8, resolve: u8,
    presence: u8, manipulation: u8, composure: u8,
    brawl: u8, weaponry: u8, firearms: u8, athletics: u8,
    primal_urge: u8,
) -> PyResult<String> {
    let essence_max = crate::splats::werewolf::essence_max(primal_urge);
    let b = BuildDefinition {
        id, name: name.to_string(), splat: Splat::Werewolf,
        attributes: Attributes::new(strength, dexterity, stamina, intelligence, wits, resolve, presence, manipulation, composure),
        skills: CombatSkills { brawl, weaponry, firearms, athletics, stealth: 0 },
        weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
        splat_data: SplatBuild::Werewolf { primal_urge, essence_max, purity: 0, glory: 0, cunning: 0, honor: 0, wisdom: 0 },
        size: 5, merits: std::collections::HashMap::new(),
    };
    serde_json::to_string(&b).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// Build a changeling BuildDefinition as JSON.
#[pyfunction]
pub fn make_changeling_json(
    id: u32, name: &str,
    strength: u8, dexterity: u8, stamina: u8,
    intelligence: u8, wits: u8, resolve: u8,
    presence: u8, manipulation: u8, composure: u8,
    brawl: u8, weaponry: u8, firearms: u8, athletics: u8,
    wyrd: u8,
    seeming: &str,
) -> PyResult<String> {
    use crate::character::Seeming;
    let seeming_val = match seeming.to_lowercase().as_str() {
        "beast"    => Seeming::Beast,
        "darkling" => Seeming::Darkling,
        "elemental"=> Seeming::Elemental,
        "fairest"  => Seeming::Fairest,
        "ogre"     => Seeming::Ogre,
        "wizened"  => Seeming::Wizened,
        other => return Err(pyo3::exceptions::PyValueError::new_err(
            format!("unknown seeming: {other}")
        )),
    };
    let glamour_max = crate::splats::changeling::glamour_max(wyrd);
    let b = BuildDefinition {
        id, name: name.to_string(), splat: Splat::Changeling,
        attributes: Attributes::new(strength, dexterity, stamina, intelligence, wits, resolve, presence, manipulation, composure),
        skills: CombatSkills { brawl, weaponry, firearms, athletics, stealth: 0 },
        weapon: WeaponProfile::unarmed(), armor: ArmorProfile::none(),
        splat_data: SplatBuild::Changeling { wyrd, glamour_max, seeming: seeming_val },
        size: 5, merits: std::collections::HashMap::new(),
    };
    serde_json::to_string(&b).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// Parse a JSON list of builds from Python (used by VecEnv and build registry).
pub fn parse_builds(builds_json: &str) -> PyResult<Vec<BuildDefinition>> {
    serde_json::from_str(builds_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

