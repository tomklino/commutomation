import sys
import os
import pytz
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser('.patched_modules/israel-rail-api'))
import israelrailapi

def make_serializable(obj):
    """Recursively convert objects to JSON-serializable format"""
    if hasattr(obj, '__dict__'):
        # Convert object to dictionary
        result = {}
        for key, value in obj.__dict__.items():
            result[key] = make_serializable(value)
        return result
    elif isinstance(obj, (list, tuple)):
        # Handle lists and tuples
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        # Handle dictionaries
        return {key: make_serializable(value) for key, value in obj.items()}
    else:
        # Return primitive types as-is
        return obj

def find_optimal_departure_time(routes, min_departure_gap=5, max_arrival_diff=10):
    """
    Find a departure time such that a train departing at least min_departure_gap minutes later
    will arrive no more than max_arrival_diff minutes later than the first train.
    
    Args:
        routes: List of train routes from israelrailapi
        min_departure_gap: Minimum minutes between departures (default: 5)
        max_arrival_diff: Maximum minutes difference in arrival times (default: 10)
    
    Returns:
        dict: Best departure time info or None if no suitable time found
    """
    # Extract all trains from all routes
    all_trains = []
    for route in routes:
        for train in route.trains:
            all_trains.append({
                'departure': datetime.fromisoformat(train.departure.replace('Z', '+00:00')),
                'arrival': datetime.fromisoformat(train.arrival.replace('Z', '+00:00')),
                'train_number': train.data.trainNumber,
                'route_info': f"Train {train.data.trainNumber}"
            })
    
    # Sort trains by departure time
    all_trains.sort(key=lambda x: x['departure'])
    
    best_option = None
    best_time_saved = timedelta(0)
    
    # Check each train as a potential first departure
    for i, first_train in enumerate(all_trains):
        first_departure = first_train['departure']
        first_arrival = first_train['arrival']
        
        # Find trains that depart at least min_departure_gap minutes later
        min_later_departure = first_departure + timedelta(minutes=min_departure_gap)
        
        for j, later_train in enumerate(all_trains[i+1:], i+1):
            if later_train['departure'] >= min_later_departure:
                later_arrival = later_train['arrival']
                
                # Check if arrival difference is within acceptable range
                arrival_diff = later_arrival - first_arrival
                if arrival_diff <= timedelta(minutes=max_arrival_diff):
                    # Calculate time saved by taking the later train
                    time_saved = later_train['departure'] - first_departure
                    
                    if best_option is None or time_saved > best_time_saved:
                        best_option = {
                            'first_train': first_train,
                            'later_train': later_train,
                            'departure_gap_minutes': (later_train['departure'] - first_departure).total_seconds() / 60,
                            'arrival_diff_minutes': arrival_diff.total_seconds() / 60,
                            'time_saved_minutes': time_saved.total_seconds() / 60
                        }
                        best_time_saved = time_saved
                else:
                    # Since trains are sorted by departure time, if this one is too late,
                    # all subsequent ones will be even later
                    break
    
    return best_option

def find_optimal_departure_time_from_serialized(serialized_data, arrival_date, arrival_time, min_departure_gap=5, max_arrival_diff=10):
    """
    Find a departure time such that a route departing at least min_departure_gap minutes later
    will arrive no more than max_arrival_diff minutes later than the first route, and both routes
    arrive by the specified arrival date and time.
    """
    # Define the Jerusalem timezone
    jerusalem_tz = pytz.timezone('Asia/Jerusalem')

    # Parse target arrival datetime
    target_arrival_naive = datetime.strptime(f"{arrival_date} {arrival_time}", "%Y-%m-%d %H%M")
    
    # Make the target_arrival object "aware" of the Jerusalem timezone.
    target_arrival = jerusalem_tz.localize(target_arrival_naive)

    # Extract all routes with their start_time and end_time, filtering by arrival time
    all_routes = []
    for route in serialized_data:
        route_arrival = jerusalem_tz.localize(datetime.fromisoformat(route['end_time']))
        
        # Now, both datetimes are "aware" and can be compared accurately
        if route_arrival <= target_arrival:
            all_routes.append({
                'departure': jerusalem_tz.localize(datetime.fromisoformat(route['start_time'])),
                'arrival': route_arrival,
                'trains': route['trains'],
                'route_info': f"Route with {len(route['trains'])} train(s)"
            })
    
    # ... (rest of the function remains the same) ...
    # Sort routes by departure time
    all_routes.sort(key=lambda x: x['departure'])
    
    # Collect all possible options
    all_options = []
    
    # Check each route as a potential first departure
    for i, first_route in enumerate(all_routes):
        first_departure = first_route['departure']
        first_arrival = first_route['arrival']
        
        # Find routes that depart at least min_departure_gap minutes later
        min_later_departure = first_departure + timedelta(minutes=min_departure_gap)
        
        for j, later_route in enumerate(all_routes[i+1:], i+1):
            if later_route['departure'] >= min_later_departure:
                later_arrival = later_route['arrival']
                
                # Check if arrival difference is within acceptable range
                arrival_diff = later_arrival - first_arrival
                if arrival_diff <= timedelta(minutes=max_arrival_diff):
                    # Calculate time saved by taking the later route
                    time_saved = later_route['departure'] - first_departure
                    
                    option = {
                        'first_route': first_route,
                        'later_route': later_route,
                        'departure_gap_minutes': (later_route['departure'] - first_departure).total_seconds() / 60,
                        'arrival_diff_minutes': arrival_diff.total_seconds() / 60,
                        'time_saved_minutes': time_saved.total_seconds() / 60,
                        'target_arrival': target_arrival
                    }
                    all_options.append(option)
                else:
                    # Since routes are sorted by departure time, if this one is too late,
                    # all subsequent ones will be even later
                    break
    
    # Sort options by arrival time of the first train
    all_options.sort(key=lambda x: x['first_route']['arrival'])
    
    return all_options

def handle_request(source="", dest="", arrival_date="", arrival_time=""):
    s = israelrailapi.TrainSchedule()

    from_date = arrival_date
    from_time = (datetime.strptime(arrival_time, "%H%M") - timedelta(hours=1)).strftime("%H%M")
    q = s.query("tel aviv savidor center", "hod hasharon sokolov", from_date, from_time)

    serializable_data = make_serializable(q)

    # Find optimal departure time using serialized data
    all_options = find_optimal_departure_time_from_serialized(serializable_data, arrival_date, arrival_time, max_arrival_diff=10)
    if all_options:
        return all_options[-1]
    return None

if __name__ == "__main__":
    print(israelrailapi)