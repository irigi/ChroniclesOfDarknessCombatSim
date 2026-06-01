use pyo3::prelude::*;
use rayon::prelude::*;

use crate::env::{SimEnv, parse_builds};

/// Vectorised environment: N independent simulation environments stepped in parallel.
///
/// All environments share the same build/team configuration by default.
/// Use `reset_env(i, builds_json, teams, seed)` to reconfigure individual envs
/// with different matchups (needed for diverse self-play training).
#[pyclass]
pub struct VecEnv {
    envs: Vec<SimEnv>,
}

#[pymethods]
impl VecEnv {
    /// Create N environments with the same builds and team layout.
    #[new]
    fn new(builds_json: &str, teams: Vec<u8>, n_envs: usize) -> PyResult<Self> {
        let builds = parse_builds(builds_json)?;
        if builds.len() != teams.len() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "builds and teams must have the same length",
            ));
        }
        let envs = (0..n_envs)
            .map(|_| SimEnv::new(builds.clone(), teams.clone()))
            .collect();
        Ok(Self { envs })
    }

    /// Reset all environments and return a list of observations.
    /// Seeds default to sequential integers per env.
    fn reset_all(&mut self) -> Vec<Vec<f32>> {
        self.envs
            .par_iter_mut()
            .enumerate()
            .map(|(i, env)| env.reset(Some(i as u64)))
            .collect()
    }

    /// Reset a single environment (optionally with a new build configuration).
    #[pyo3(signature = (env_idx, builds_json=None, teams=None, seed=None))]
    fn reset_env(
        &mut self,
        env_idx: usize,
        builds_json: Option<&str>,
        teams: Option<Vec<u8>>,
        seed: Option<u64>,
    ) -> PyResult<Vec<f32>> {
        if env_idx >= self.envs.len() {
            return Err(pyo3::exceptions::PyIndexError::new_err(
                format!("env_idx {} out of range (n_envs={})", env_idx, self.envs.len()),
            ));
        }
        if let (Some(bj), Some(t)) = (builds_json, teams) {
            let builds = parse_builds(bj)?;
            self.envs[env_idx] = SimEnv::new(builds, t);
        }
        Ok(self.envs[env_idx].reset(seed))
    }

    /// Step all environments in parallel. `actions[i]` is the action for env i.
    /// Returns (obs_list, rewards, terminated_list, truncated_list).
    fn step_all(
        &mut self,
        actions: Vec<usize>,
    ) -> PyResult<(Vec<Vec<f32>>, Vec<f32>, Vec<bool>, Vec<bool>)> {
        if actions.len() != self.envs.len() {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "actions length {} != n_envs {}",
                actions.len(),
                self.envs.len()
            )));
        }
        let results: Vec<(Vec<f32>, f32, bool, bool)> = self
            .envs
            .par_iter_mut()
            .zip(actions.par_iter())
            .map(|(env, &action)| env.step(action))
            .collect();

        let mut obs = Vec::with_capacity(self.envs.len());
        let mut rewards = Vec::with_capacity(self.envs.len());
        let mut terminated = Vec::with_capacity(self.envs.len());
        let mut truncated = Vec::with_capacity(self.envs.len());
        for (o, r, t, tr) in results {
            obs.push(o);
            rewards.push(r);
            terminated.push(t);
            truncated.push(tr);
        }
        Ok((obs, rewards, terminated, truncated))
    }

    /// Return the action mask for every environment.
    fn action_masks_all(&self) -> Vec<Vec<bool>> {
        self.envs.par_iter().map(|e| e.action_mask()).collect()
    }

    /// Number of environments.
    fn n_envs(&self) -> usize {
        self.envs.len()
    }

    fn obs_size(&self) -> usize {
        self.envs.first().map(|e| e.obs_size()).unwrap_or(0)
    }

    fn action_space_size(&self) -> usize {
        crate::action::ACTION_SPACE_SIZE
    }

    fn is_done(&self, env_idx: usize) -> bool {
        self.envs.get(env_idx).map(|e| e.is_done()).unwrap_or(true)
    }
}
