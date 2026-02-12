# Schelling Model with Caching and Replay

## Summary

This example applies caching on the Mesa [Schelling example](https://github.com/mesa/mesa-examples/tree/main/examples/schelling).
It enables a simulation run to be "cached" or in other words recorded. The recorded simulation run is persisted on the local file system and can be replayed at any later point.

It uses the [Mesa-Replay](https://github.com/Logende/mesa-replay) library and puts the Schelling model inside a so-called `CacheableModel` wrapper that we name `CacheableSchelling`.
From the user's perspective, the new model behaves the same way as the original Schelling model, but additionally supports caching.

Note that the main purpose of this example is to demonstrate that caching and replaying simulation runs is possible.
The example is designed to be accessible.
In practice, someone who wants to replay their simulation might not necessarily embed a replay button into the web view, but instead have a dedicated script to run a simulation that is being cached, separate from a script to replay a simulation run from a given cache file.
More examples of caching and replay can be found in the [Mesa-Replay Repository](https://github.com/Logende/mesa-replay/tree/main/examples).

## Installation

To install the dependencies use pip and the requirements.txt in this directory. e.g.

```
    $ pip install -r requirements.txt
```

## How to Run

To run the model interactively, run ``solara run server.py`` in this directory. e.g.

```
    $ solara run server.py
```

or

Run the cacheable version with replay support:

```
    $ solara run run.py
```

Then open your browser to [http://localhost:8765](http://localhost:8765) and press Reset, then Run.

### Recording a Simulation

1. **Disable** the 'Replay cached run?' checkbox
2. Click **Reset** to create a new model
3. Click **Run** to start the simulation
4. **Wait for the simulation to complete** - the model will run until all agents are happy (or you stop it manually)
5. The cache file will be created **automatically when the simulation finishes**

**Important:** The cache file is only written to disk when the simulation completes (when `model.running` becomes `False`). The model state is stored in memory during the simulation and written all at once at the end. If you stop the server before the simulation completes, no cache file will be created.

### Replaying a Simulation

1. **Enable** the 'Replay cached run?' checkbox
2. Click **Reset** to load the cached simulation
3. Click **Run** to replay the cached steps

The replay will show the exact same sequence of states that were recorded.

## Troubleshooting

### Cache file not created

If the cache file is not being created:

1. **Check the file path**: Make sure the path you entered is valid and the directory exists. You can use:
   - Relative paths: `./my_cache.cache`
   - Absolute paths: `/Users/yourname/simulations/cache.cache`
   - Default: `./my_cache_file_path.cache`

2. **Stop the simulation**: The cache file is created when:
   - The simulation completes naturally (all agents happy), OR
   - You manually click the pause button to stop it
   - Check terminal output for "Wrote CacheableModel cache file to ..." message

3. **Verify Python version**: Run `python --version` and ensure you have Python 3.10 or higher. The mesa-replay library requires modern Python.

4. **Check for errors**: Look at the terminal output for any serialization errors. With Mesa 3.x, the default serialization should work without issues.

5. **Test manually**: Run the included test scripts to diagnose issues:
   ```bash
   python test_cache_creation.py
   python test_full_simulation.py
   python test_manual_stop.py
   ```

### Common Issues

- **TypeError about `|` operator**: Upgrade to Python 3.10+
- **File not found during replay**: Make sure you've run a complete simulation first with replay disabled
- **Replay shows different results**: This shouldn't happen - if it does, there may be an issue with the random seed or serialization

## Mesa 3.x Compatibility

This example has been tested with Mesa 3.x and uses the default serialization provided by mesa-replay with `dill`. The serialization successfully handles Mesa 3.x internal structures including:

- `AgentSet` objects
- `OrthogonalMooreGrid` and other grid types
- `Random` instances
- `DataCollector` objects

No custom serialization is required for basic models. If you have a complex model with custom objects that don't serialize well, you can override the `_serialize_state()` and `_deserialize_state()` methods in your `CacheableModel` subclass.

## Files

* ``run.py``: Launches a model visualization server and uses `CacheableSchelling` as simulation model with cache file path input
* ``cacheablemodel.py``: Implements `CacheableSchelling` with manual stop support to make the original Schelling model cacheable
* ``model.py``: The Schelling segregation model (Mesa 3.x version)
* ``server.py``: Non-cacheable version visualization (for comparison)
* ``test_cache_creation.py``: Diagnostic test for cache file creation
* ``test_full_simulation.py``: Full simulation test with recording and replay
* ``test_manual_stop.py``: Test manual stop functionality and custom file paths

## Further Reading

* [Mesa-Replay library](https://github.com/Logende/mesa-replay)
* [More caching and replay examples](https://github.com/Logende/mesa-replay/tree/main/examples)
