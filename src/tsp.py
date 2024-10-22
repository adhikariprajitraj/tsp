import json
import math
from itertools import combinations
import gurobipy as gp
from gurobipy import GRB
import folium


def haversine(coord1, coord2):
    # Calculate the great circle distance between two points
    # on the earth (specified in decimal degrees)
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    radius = 6371  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2) * math.sin(dlat/2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2) * math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = radius * c
    return distance


# Load city data
with open('data/cities.json') as f:
    cities = json.load(f)

# Prepare distance dictionary
distances = {
    (c1, c2): haversine(
        (cities[c1]['lat'], cities[c1]['long']),
        (cities[c2]['lat'], cities[c2]['long'])
    )
    for c1, c2 in combinations(cities.keys(), 2)
}

# Model setup
model = gp.Model("TSP")
vars = model.addVars(
    distances.keys(), obj=distances, vtype=GRB.BINARY, name='route'
)
model.addConstrs(
    vars.sum(c, '*') + vars.sum('*', c) == 2 for c in cities
)
model.setObjective(
    gp.quicksum(distances[i, j] * vars[i, j] for i, j in distances),
    GRB.MINIMIZE
)
model.Params.lazyConstraints = 1
model.optimize()


# Extract the tour from the model
def extract_tour(vars):
    # Creating a dictionary to hold the edges
    edge_dict = {(i, j): vars[i, j].X for i, j in vars.keys() if vars[i, j].X > 0.5}
    if not edge_dict:
        raise ValueError("No edges in the tour. Check model constraints and data validity.")

    # Starting from an arbitrary edge
    start, _ = next(iter(edge_dict))
    tour = [start]
    while True:
        # Find next city that forms an edge with current city
        next_cities = [j for (i, j) in edge_dict if i == tour[-1]]
        if not next_cities:
            break
        next_city = next_cities[0]
        tour.append(next_city)
        # Remove the edge from the dictionary to prevent looping back
        edge_dict.pop((tour[-2], next_city), None)
        
        # If tour has returned to the starting city, complete the loop
        if tour[-1] == start:
            break

    if len(tour) <= 1:
        raise ValueError("Incomplete tour. Ensure model's feasibility and correctness of constraints.")

    return tour



tour = extract_tour(vars)

# Map visualization
map = folium.Map(
    location=[cities[tour[0]]['lat'], cities[tour[0]]['long']],
    zoom_start=7
)
folium.PolyLine([(cities[city]['lat'], cities[city]['long']) for city in tour + [tour[0]]]).add_to(map)
map.save('map_visualization.html')

# Clean up model environment
model.dispose()
