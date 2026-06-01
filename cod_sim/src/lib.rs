mod action;
mod character;
mod combat;
mod dice;
mod env;
pub mod splats;
mod vec_env;

use pyo3::prelude::*;

use crate::env::{CombatEnv, make_mortal_json, make_vampire_json, make_werewolf_json, make_changeling_json};
use crate::vec_env::VecEnv;

#[pymodule]
fn cod_sim(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CombatEnv>()?;
    m.add_class::<VecEnv>()?;
    m.add_function(wrap_pyfunction!(make_mortal_json, m)?)?;
    m.add_function(wrap_pyfunction!(make_vampire_json, m)?)?;
    m.add_function(wrap_pyfunction!(make_werewolf_json, m)?)?;
    m.add_function(wrap_pyfunction!(make_changeling_json, m)?)?;
    m.add("ACTION_SPACE_SIZE", crate::action::ACTION_SPACE_SIZE)?;
    m.add("OBS_PER_CHAR", crate::env::OBS_PER_CHAR)?;
    m.add("GLOBAL_OBS", crate::env::GLOBAL_OBS)?;
    Ok(())
}
