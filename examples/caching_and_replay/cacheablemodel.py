from mesa_replay import CacheableModel, CacheState
from model import Schelling
from pathlib import Path
import dill  # Explicitly import dill for serialization
import random
import weakref
from mesa.agent import AgentSet
from mesa.discrete_space import OrthogonalMooreGrid
from model import SchellingAgent

class CacheableSchelling(CacheableModel):
    """A wrapper around the original Schelling model to make the simulation cacheable
    and replay-able.  Uses CacheableModel from the Mesa-Replay library,
    which is a wrapper that can be put around any regular mesa model to make it
    "cacheable".
    From outside, a CacheableSchelling instance can be treated like any
    regular Mesa model.
    The only difference is that the model will write the state of every simulation step
    to a cache file or when in replay mode use a given cache file to replay that cached
    simulation run.
    """

    def __init__(
        self,
        width=20,
        height=20,
        density=0.8,
        minority_pc=0.2,
        homophily=3,
        radius=1,
        cache_file_path="./my_cache_file_path.cache",
        replay=False,
        verbose=False,
    ):
        """Initialize a cacheable Schelling model.
        
        Args:
            width: Width of the grid
            height: Height of the grid
            density: Initial population density
            minority_pc: Percentage of minority agents
            homophily: Minimum number of similar neighbors needed to be happy
            radius: Neighborhood radius for checking similarity
            cache_file_path: Path where cache file will be saved/loaded
            replay: If True, replay from cache file. If False, run simulation and record.
            verbose: If True, print detailed status messages
        """
        actual_model = Schelling(
            width=width,
            height=height,
            density=density,
            minority_pc=minority_pc,
            homophily=homophily,
            radius=radius,
        )

        self.verbose = verbose
        
        cache_path = Path(cache_file_path)
        effective_replay = replay and cache_path.exists() and cache_path.is_file()

        if replay and not effective_replay:
            print(
                f"Warning: Replay requested but cache file not found ({cache_file_path}). "
                "Falling back to normal simulation (recording mode)."
            )

        cache_state = CacheState.REPLAY if effective_replay else CacheState.RECORD
        
        if verbose:
            mode = "REPLAY" if cache_state == CacheState.REPLAY else "RECORD"
            print(f"Initializing CacheableSchelling in {mode} mode")
            print(f"  Cache file: {cache_file_path}")
            if cache_state == CacheState.REPLAY:
                print(f"  Will replay from existing cache")
            else:
                print(f"  Will record simulation (cache written when simulation completes)")

        super().__init__(
            model=actual_model,
            cache_file_path=cache_file_path,
            cache_state=cache_state,
        )

    def step(self):
        """Execute one step of the model.
        
        The base CacheableModel class automatically handles:
        - Writing cache in RECORD mode
        - Reading from cache in REPLAY mode
        """
        super().step()
        
        # In RECORD mode, write cache after each step for incremental persistence
        # In REPLAY mode, the base class already read from cache, don't write
        if self._cache_state == CacheState.RECORD:
            self._write_cache_file()
            
        if self.verbose:
            mode = "REPLAY" if self._cache_state == CacheState.REPLAY else "RECORD"
            print(f"Step {self.step_count} ({mode} mode)")

    def __setattr__(self, key, value):
        """Override to finalize cache when model is stopped."""
        if key == "running":
            was_running = getattr(self.model, 'running', True) if hasattr(self, 'model') else True
            if hasattr(self, 'model'):
                self.model.__setattr__(key, value)
            else:
                super().__setattr__(key, value)
            
            if hasattr(self, '_cache_state') and was_running and not value:
                if self._cache_state == CacheState.RECORD and not self.run_finished:
                    print(f"Simulation stopped at step {self.step_count}. Finalizing cache file...")
                    self.finish_run()
        else:
            super().__setattr__(key, value)

    def _serialize_state(self) -> bytes:
        state_dict = self.model.__dict__.copy()

        # 1. Random state
        state_dict['random_state'] = self.model.random.getstate()
        state_dict.pop('random', None)

        # 2. Agents → list of dicts (save cell coordinates)
        agents_data = []
        for agent in self.model.agents:
            # For CellAgents, pos is always None - use cell.coordinate instead
            coord = agent.cell.coordinate if hasattr(agent, 'cell') and agent.cell else None
            agents_data.append({
                'unique_id': agent.unique_id,
                'type': agent.type,
                'coord': coord,  # Save cell coordinate
            })
        state_dict['agents_data'] = agents_data
        state_dict.pop('agents', None)
        state_dict.pop('_agents', None)           # Mesa 3.x internal
        state_dict.pop('_agents_by_type', None)

        # 3. Grid contents (agent IDs per cell)
        grid_data = {}
        for coord, cell in self.model.grid._cells.items():
            grid_data[coord] = [a.unique_id for a in cell.agents]
        state_dict['grid_data'] = grid_data
        state_dict.pop('grid', None)

        # 4. DataCollector – save the entire collected data
        if hasattr(self.model, 'datacollector'):
            dc = self.model.datacollector
            state_dict['datacollector_data'] = {
                'model_vars': dc.model_vars.copy(),
                'agent_records': dc._agent_records.copy() if hasattr(dc, '_agent_records') else {},
            }

        # 5. Next ID counter (save the private attribute Mesa uses)
        state_dict['_next_id'] = self.model.agent_id_counter if hasattr(self.model, 'agent_id_counter') else getattr(self.model, '_next_id', 0)

        return dill.dumps(state_dict)

    def _deserialize_state(self, state: bytes) -> None:
        if self.verbose:
            print(f"\n=== _deserialize_state called at step {self.step_count} ===")
        state_dict = dill.loads(state)

        # Restore basic attributes first
        for k, v in state_dict.items():
            if k not in ['random_state', 'agents_data', 'grid_data', 'datacollector_data', '_next_id']:
                setattr(self.model, k, v)

        # Random
        self.model.random = random.Random()
        self.model.random.setstate(state_dict['random_state'])

        # Grid
        self.model.grid = OrthogonalMooreGrid(
            (self.model.width, self.model.height),
            torus=True,
            random=self.model.random
        )

        # Clear existing agents before restoring (avoid duplicates)
        if self.verbose:
            print(f"  Before clearing: {len(self.model._agents)} agents in model")
        self.model._agents.clear()  # Clear main agent dict
        # Also clear other agent tracking dicts if they exist
        if hasattr(self.model, '_agents_by_type'):
            self.model._agents_by_type.clear()
        if hasattr(self.model, '_all_agents'):
            self.model._all_agents.clear()
        if self.verbose:
            print(f"  After clearing: {len(self.model._agents)} agents in model")

        # Agents - Restore from serialized data
        agent_map = {}
        agents_to_restore = state_dict.get('agents_data', [])
        if self.verbose:
            print(f"  Restoring {len(agents_to_restore)} agents from cache")
        
        for a_data in agents_to_restore:
            agent = SchellingAgent(self.model, a_data['type'])
            agent.unique_id = a_data['unique_id']  # Override the auto-assigned ID
            coord = a_data.get('coord')  # Get cell coordinate from serialized data
            
            # Properly place agent in cell
            if coord is not None and coord in self.model.grid._cells:
                cell = self.model.grid._cells[coord]
                # For CellAgent, setting agent.cell should handle everything
                agent.cell = cell
            elif self.verbose:
                print(f"Warning: Agent {agent.unique_id} has no valid position, skipping placement")
                    
            agent_map[a_data['unique_id']] = agent
        
        if self.verbose:
            print(f"  After restoration loop: {len(self.model._agents)} agents in model")

        # Grid consistency: Agents are already placed in cells above (agent.cell = cell)
        # No need to manually reconstruct cell.agents as it's populated during agent restoration

        # DataCollector restoration - simply restore the saved state
        if 'datacollector_data' in state_dict and hasattr(self.model, 'datacollector'):
            dc_data = state_dict['datacollector_data']
            # Directly replace datacollector data with cached values
            # This prevents double-counting when model.step() collects data again
            self.model.datacollector.model_vars = dc_data['model_vars'].copy()
            if 'agent_records' in dc_data and hasattr(self.model.datacollector, '_agent_records'):
                self.model.datacollector._agent_records = dc_data['agent_records'].copy()

        # Restore the internal next_id counter
        self.model.agent_id_counter = state_dict.get('_next_id', 0)

        # Validate restoration
        if self.verbose:
            print(f"Restored state at step {self.step_count}")
            print(f"  Agents in _agents dict: {len(self.model._agents)}")
            print(f"  Agents via .agents property: {len(self.model.agents)}")
            agents_with_cells = sum(1 for a in self.model.agents if hasattr(a, 'cell') and a.cell)
            print(f"  Agents with cells: {agents_with_cells}")
            print(f"=== End of _deserialize_state ===\n")