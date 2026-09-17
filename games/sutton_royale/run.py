"""Main file for generating results for Sutton Royale."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    # This container has 4 CPUs / 16GB RAM. num_threads/batching_size are
    # sized to that, not to a generic "more is faster" default: bonus,
    # super_bonus and royale_mystery are 100%-guaranteed-feature modes (every
    # sim runs a full free-spin sequence, unlike base/sutton_spins where most
    # sims are cheap single reveals) and accumulate ~0.5MB/sim in memory
    # before their one flush per batch. At the old 10 threads / 10,000
    # batching_size, 10 parallel processes each held ~1GB+ in memory at once
    # (num_repeats rounds to 1 at these sim counts, so nothing flushed until
    # the whole per-thread share was done) - within a hair of the box's 16GB,
    # and enough to OOM some worker processes mid-batch (observed directly:
    # missing per-thread temp files after a `bonus` run, 3 of 10 threads
    # never reaching their flush). 4 threads (= nproc) avoids oversubscribing
    # the CPUs; 1,000 batching_size keeps peak memory per thread bounded
    # regardless of how rich a mode's average book is.
    num_threads = 4
    rust_threads = 4
    batching_size = 1000
    compression = True
    profiling = False

    # v7 verification pass (SPEC.md section 10): build/verify at reduced sim
    # counts with optimization off before committing to the full run below.
    num_sim_args = {
        "base": 50_000,
        "mystery_enhancer": 30_000,
        "sutton_spins": 50_000,
        "bonus": 20_000,
        "super_bonus": 20_000,
        "royale_mystery": 20_000,
        "max_or_zero": 20_000,
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "run_format_checks": False,
    }
    target_modes = list(num_sim_args.keys())

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        custom_keys = [{"symbol": "scatter"}]
        create_stat_sheet(gamestate, custom_keys=custom_keys)

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)
