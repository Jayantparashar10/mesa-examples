"""Cacheable Schelling model visualization with replay functionality.

This module extends the basic Schelling visualization to support
caching and replaying simulation runs.
"""

import solara
from mesa.visualization import SolaraViz, make_plot_component, make_space_component
from mesa.visualization.utils import update_counter
from cacheablemodel import CacheableSchelling
from server import agent_portrayal, get_happy_agents, model_params
from mesa_replay import CacheState
from pathlib import Path

# Add replay parameter to model params
model_params["replay"] = {
    "type": "Checkbox",
    "value": False,
    "label": "Replay cached run?",
}
model_params["cache_file_path"] = {
    "type": "InputText",
    "value": "./my_cache_file_path.cache",
    "label": "Cache File Path",
}


@solara.component
def get_cache_file_status(model):
    """Display cache file status and usage instructions.
    
    Args:
        model: The CacheableSchelling model instance.
    """
    
    update_counter.get()
    
    cache_file = Path(model.cache_file_path)
    exists = cache_file.exists() and cache_file.is_file()
    
    if model._cache_state == CacheState.REPLAY:
        instructions = (
            f"Currently replaying cached simulation from step 0 to step {len(model.cache) - 1 if hasattr(model, 'cache') else 'unknown'}.  \n"
            f"Each step shows the exact state that was recorded."
        )
    elif model._cache_state == CacheState.RECORD:
        instructions = (
            "Simulation is being recorded automatically.  \n"
            f"Cache file is updated after each step and finalized when the simulation stops or converges."
        )
    # else:
    #     status = "⚠️ **Unknown state**"
    #     instructions = ""
    
    file_size = ""
    if exists:
        size_bytes = cache_file.stat().st_size
        if size_bytes < 1024:
            file_size = f" ({size_bytes} bytes)"
        elif size_bytes < 1024 * 1024:
            file_size = f" ({size_bytes / 1024:.1f} KB)"
        else:
            file_size = f" ({size_bytes / (1024 * 1024):.1f} MB)"
    
    solara.Markdown(
        f"\n \n"
        f"\n \n"
        f"\n \n"

        f"---  \n"
        f"**File:** `{cache_file}`{file_size}  \n"
        f"**Exists:** {'✅ Yes' if exists else '❌ No'}  \n\n"
        f"{instructions}  \n\n"
        f"---  \n"
        f"**Quick Guide:**  \n"
        f"1. **Record:** Set file path, uncheck 'Replay', click Reset & Run  \n"
        f"2. **Replay:** Check 'Replay', click Reset & Run to see recorded simulation  \n"
        f"*Note: Cache is saved automatically during and at the end of the run.*"
    )


# Initialize cacheable model
model = CacheableSchelling()

# Create visualization components
space_component = make_space_component(agent_portrayal)
happy_chart = make_plot_component("happy")

# Create the Solara visualization page
Page = SolaraViz(
    model,
    components=[
        space_component,
        happy_chart,
        get_happy_agents,
        get_cache_file_status,
    ],
    model_params=model_params,
    name="Schelling Segregation Model (Cacheable)",
)