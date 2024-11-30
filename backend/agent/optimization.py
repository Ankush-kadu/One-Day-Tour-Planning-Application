from typing import List, Dict, Any, Tuple
from datetime import datetime, time
import ollama
from ..models.schemas import Location, ItineraryStop
import networkx as nx

class OptimizationAgent:
    def __init__(self):
        self.transport_modes = {
            'walking': {'cost_per_km': 0, 'speed_kmh': 4},
            'taxi': {'cost_per_km': 2, 'speed_kmh': 30},
            'public_transport': {'cost_per_km': 0.5, 'speed_kmh': 20}
        }

    async def optimize_route(
        self,
        stops: List[ItineraryStop],
        budget: float,
        start_time: time,
        end_time: time,
        starting_point: Location = None
    ) -> Tuple[List[ItineraryStop], float]:
        # Create a graph for optimization
        G = self._create_travel_graph(stops, starting_point)
        
        # Calculate optimal path considering time and budget constraints
        optimized_path = self._calculate_optimal_path(G, budget)
        
        # Assign time slots to each stop
        scheduled_stops = self._assign_time_slots(optimized_path, start_time, end_time)
        
        # Calculate total cost
        total_cost = self._calculate_total_cost(scheduled_stops)
        
        return scheduled_stops, total_cost

    def _create_travel_graph(self, stops: List[ItineraryStop], starting_point: Location = None) -> nx.Graph:
        G = nx.Graph()
        
        # Add all stops as nodes
        locations = [starting_point] + [stop.location for stop in stops] if starting_point else [stop.location for stop in stops]
        
        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                if i != j:
                    # Calculate distance and possible transport modes
                    distance = self._calculate_distance(loc1, loc2)
                    
                    # Add edges for each transport mode
                    for mode, params in self.transport_modes.items():
                        travel_time = (distance / params['speed_kmh']) * 60  # in minutes
                        travel_cost = distance * params['cost_per_km']
                        
                        G.add_edge(
                            loc1.name,
                            loc2.name,
                            mode=mode,
                            distance=distance,
                            time=travel_time,
                            cost=travel_cost
                        )
        
        return G

    def _calculate_optimal_path(self, G: nx.Graph, budget: float) -> List[Dict[str, Any]]:
        # Use modified Dijkstra's algorithm considering both time and cost
        optimal_path = []
        nodes = list(G.nodes())
        
        current_node = nodes[0]
        remaining_nodes = set(nodes[1:])
        current_cost = 0
        
        while remaining_nodes:
            best_next = None
            best_score = float('inf')
            best_mode = None
            
            for next_node in remaining_nodes:
                for mode in self.transport_modes:
                    edge_data = G.get_edge_data(current_node, next_node)
                    if edge_data and edge_data[mode]['cost'] + current_cost <= budget:
                        # Score based on combination of time and cost
                        score = edge_data[mode]['time'] + (edge_data[mode]['cost'] * 10)
                        if score < best_score:
                            best_score = score
                            best_next = next_node
                            best_mode = mode
            
            if best_next is None:
                break
                
            optimal_path.append({
                'from': current_node,
                'to': best_next,
                'mode': best_mode,
                'time': G[current_node][best_next][best_mode]['time'],
                'cost': G[current_node][best_next][best_mode]['cost']
            })
            
            current_cost += G[current_node][best_next][best_mode]['cost']
            current_node = best_next
            remaining_nodes.remove(best_next)
        
        return optimal_path

    def _assign_time_slots(
        self,
        path: List[Dict[str, Any]],
        start_time: time,
        end_time: time
    ) -> List[ItineraryStop]:
        # Convert times to minutes for easier calculation
        current_time = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        scheduled_stops = []
        
        for segment in path:
            # Add travel time to current time
            current_time += segment['time']
            
            # Assign typical duration for the stop (simplified)
            stop_duration = 60  # Default 1 hour per stop
            
            if current_time + stop_duration <= end_minutes:
                stop = ItineraryStop(
                    location=segment['to'],
                    start_time=self._minutes_to_time(current_time),
                    end_time=self._minutes_to_time(current_time + stop_duration),
                    travel_time_to_next=segment['time'],
                    travel_method_to_next=segment['mode'],
                    cost=segment['cost']
                )
                scheduled_stops.append(stop)
                current_time += stop_duration
            else:
                break
        
        return scheduled_stops

    def _calculate_total_cost(self, stops: List[ItineraryStop]) -> float:
        return sum(stop.cost for stop in stops)

    @staticmethod
    def _calculate_distance(loc1: Location, loc2: Location) -> float:
        # Simplified distance calculation using coordinates
        # In a real application, you'd use a proper geodesic distance calculation
        lat1, lon1 = loc1.coordinates
        lat2, lon2 = loc2.coordinates
        
        # Very simplified distance calculation
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5

    @staticmethod
    def _minutes_to_time(minutes: int) -> time:
        hours = minutes // 60
        mins = minutes % 60
        return time(hour=hours, minute=mins)