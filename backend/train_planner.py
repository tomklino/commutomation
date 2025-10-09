import sys
import os
import pytz
import json
from datetime import datetime, timedelta
import uuid
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def get_routes_data(source, dest, arrival_date, arrival_time):
    """
    Fetch and serialize route data from the Israel Rail API.
    
    Args:
        source: Source station name
        dest: Destination station name
        arrival_date: Date in YYYY-MM-DD format
        arrival_time: Time in HHMM format
    
    Returns:
        tuple: (serialized_data, jerusalem_tz, target_arrival)
    """
    logger.info(f"Fetching routes: {source} -> {dest}, arrival: {arrival_date} {arrival_time}")
    
    s = israelrailapi.TrainSchedule()
    
    # Query for routes starting 1 hour before the requested arrival time
    from_date = arrival_date
    from_time = (datetime.strptime(arrival_time, "%H%M") - timedelta(hours=1)).strftime("%H%M")
    q = s.query(source, dest, from_date, from_time)
    
    logger.info(f"API returned {len(q) if q else 0} routes")
    
    serializable_data = make_serializable(q)
    
    # Define the Jerusalem timezone and parse target arrival
    jerusalem_tz = pytz.timezone('Asia/Jerusalem')
    target_arrival_naive = datetime.strptime(f"{arrival_date} {arrival_time}", "%Y-%m-%d %H%M")
    target_arrival = jerusalem_tz.localize(target_arrival_naive)
    
    return serializable_data, jerusalem_tz, target_arrival

def filter_routes_by_arrival(serialized_data, jerusalem_tz, target_arrival):
    """
    Filter routes that arrive before the target arrival time.
    
    Args:
        serialized_data: Serialized route data
        jerusalem_tz: Jerusalem timezone object
        target_arrival: Target arrival datetime (timezone-aware)
    
    Returns:
        list: Filtered and sorted routes with departure/arrival times
    """
    all_routes = []
    for idx, route in enumerate(serialized_data):
        try:
            route_arrival = jerusalem_tz.localize(datetime.fromisoformat(route['end_time']))
            
            if route_arrival <= target_arrival:
                all_routes.append({
                    'departure': jerusalem_tz.localize(datetime.fromisoformat(route['start_time'])),
                    'arrival': route_arrival,
                    'trains': route['trains'],
                    'route_info': f"Route with {len(route['trains'])} train(s)"
                })
        except Exception as e:
            logger.error(f"Error processing route {idx}: {e}")
            logger.debug(f"Route data: {json.dumps(route, indent=2, default=str)}")
            continue
    
    logger.info(f"Filtered to {len(all_routes)} routes arriving before target time")
    
    # Sort routes by arrival time (latest to earliest)
    all_routes.sort(key=lambda x: x['arrival'], reverse=True)
    
    return all_routes

def format_route_v1(route, route_id=None):
    """
    Format a single route in the v1 API format.
    
    Args:
        route: Route dict with departure, arrival, and trains
        route_id: Optional route identifier
    
    Returns:
        dict: Formatted route structure
    """
    if route_id is None:
        route_id = str(uuid.uuid4())
    
    try:
        formatted_trains = []
        for idx, train in enumerate(route['trains']):
            try:
                # Handle different possible structures of train data
                train_number = None
                platform_number = None
                departure_time = None
                arrival_time = None
                
                # Try to get train_number from various possible locations
                if isinstance(train, dict):
                    train_number = train.get('train_number') or train.get('trainNumber')
                    if train_number is None and 'data' in train:
                        train_number = train['data'].get('trainNumber') or train['data'].get('train_number')
                    
                    platform_number = train.get('platform_number') or train.get('platformNumber') or train.get('platform')
                    if platform_number is None and 'data' in train:
                        platform_number = train['data'].get('platformNumber') or train['data'].get('platform')
                    
                    # Get departure and arrival times
                    departure_time = train.get('departure')
                    arrival_time = train.get('arrival')
                    
                    # Convert to UTC if they're strings (ISO format)
                    if isinstance(departure_time, str):
                        dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            # Assume Jerusalem time if no timezone
                            jerusalem_tz = pytz.timezone('Asia/Jerusalem')
                            dt = jerusalem_tz.localize(dt)
                        departure_time = dt.astimezone(pytz.UTC).isoformat()
                    
                    if isinstance(arrival_time, str):
                        dt = datetime.fromisoformat(arrival_time.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            # Assume Jerusalem time if no timezone
                            jerusalem_tz = pytz.timezone('Asia/Jerusalem')
                            dt = jerusalem_tz.localize(dt)
                        arrival_time = dt.astimezone(pytz.UTC).isoformat()
                
                formatted_train = {
                    'departure': departure_time,
                    'arrival': arrival_time,
                    'trainNumber': train_number,
                    'platformNumber': platform_number
                }
                formatted_trains.append(formatted_train)
                
            except Exception as e:
                logger.error(f"Error formatting train {idx} in route: {e}")
                logger.debug(f"Train data: {json.dumps(train, indent=2, default=str)}")
                raise
        
        return {
            'route_id': route_id,
            'startTime': route['departure'].astimezone(pytz.UTC).isoformat(),
            'endTime': route['arrival'].astimezone(pytz.UTC).isoformat(),
            'trains': formatted_trains
        }
    except Exception as e:
        logger.error(f"Error formatting route: {e}")
        logger.debug(f"Route data: {json.dumps(route, indent=2, default=str)}")
        raise

def find_backup_routes_for_route(all_routes, primary_route_idx, primary_route, min_departure_gap, max_arrival_diff):
    """
    Find backup routes for a specific primary route.
    
    Args:
        all_routes: List of all available routes (sorted by arrival time, latest first)
        primary_route_idx: Index of the primary route in all_routes
        primary_route: The primary route dict
        min_departure_gap: Minimum minutes between departures
        max_arrival_diff: Maximum minutes difference in arrival times
    
    Returns:
        list: Backup routes with delay information
    """
    backup_routes = []
    primary_departure = primary_route['departure']
    primary_arrival = primary_route['arrival']
    min_backup_departure = primary_departure + timedelta(minutes=min_departure_gap)
    max_backup_arrival = primary_arrival + timedelta(minutes=max_arrival_diff)
    
    logger.debug(f"Finding backups for route {primary_route.get('route_id', 'unknown')}")
    logger.debug(f"  Primary departure: {primary_departure}, arrival: {primary_arrival}")
    logger.debug(f"  Looking for departures >= {min_backup_departure} and arrivals <= {max_backup_arrival}")
    
    for idx, route in enumerate(all_routes):
        # Skip the primary route itself
        if idx == primary_route_idx:
            continue
        
        logger.debug(f"  Checking route {idx}: departure={route['departure']}, arrival={route['arrival']}")
        
        # Check if this route departs after the minimum gap
        if route['departure'] >= min_backup_departure:
            # Check if arrival time is within acceptable range
            if route['arrival'] <= max_backup_arrival:
                delay_minutes = (route['arrival'] - primary_arrival).total_seconds() / 60
                logger.debug(f"    ✓ Found backup with delay={delay_minutes} minutes")
                backup_routes.append({
                    'route_id': route.get('route_id', str(uuid.uuid4())),
                    'delayMinutes': delay_minutes
                })
            else:
                logger.debug(f"    ✗ Arrival too late: {route['arrival']} > {max_backup_arrival}")
        else:
            logger.debug(f"    ✗ Departure too early: {route['departure']} < {min_backup_departure}")
    
    logger.info(f"Found {len(backup_routes)} backup routes for route {primary_route.get('route_id', 'unknown')}")
    return backup_routes

def find_all_routes_handler(source, dest, arrival_date, arrival_time, min_departure_gap=5, max_arrival_diff=10):
    """
    Find all routes with backup options for each route.
    
    Args:
        source: Source station name
        dest: Destination station name
        arrival_date: Date in YYYY-MM-DD format
        arrival_time: Time in HHMM format
        min_departure_gap: Minimum minutes between primary and backup departures
        max_arrival_diff: Maximum minutes difference in arrival times for backups
    
    Returns:
        list: List of routes with their backup routes
    """
    try:
        # Fetch and prepare data
        serializable_data, jerusalem_tz, target_arrival = get_routes_data(source, dest, arrival_date, arrival_time)
        
        # Filter routes that arrive before target time
        all_routes = filter_routes_by_arrival(serializable_data, jerusalem_tz, target_arrival)
        
        if not all_routes:
            logger.warning("No routes found matching criteria")
            return None
        
        # Limit to 10 routes, ordered by arrival time (latest to earliest)
        all_routes = all_routes[:10]
        logger.info(f"Processing {len(all_routes)} routes")
        
        # Assign route IDs to all routes
        for route in all_routes:
            route['route_id'] = str(uuid.uuid4())
        
        # Build response with backup routes for each route
        result = []
        for idx, route in enumerate(all_routes):
            try:
                # Find backup routes for this specific route
                backup_routes = find_backup_routes_for_route(
                    all_routes, 
                    idx, 
                    route, 
                    min_departure_gap, 
                    max_arrival_diff
                )
                
                formatted_route = format_route_v1(route, route['route_id'])
                formatted_route['backupRoutes'] = backup_routes
                
                result.append({'route': formatted_route})
            except Exception as e:
                logger.error(f"Error processing route {idx}: {e}", exc_info=True)
                continue
        
        logger.info(f"Successfully formatted {len(result)} routes")
        return result if result else None
        
    except Exception as e:
        logger.error(f"Error in find_all_routes_handler: {e}", exc_info=True)
        raise

def find_optimal_departure_time_from_serialized(serialized_data, arrival_date, arrival_time, min_departure_gap=5, max_arrival_diff=10):
    """
    Find a departure time such that a route departing at least min_departure_gap minutes later
    will arrive no more than max_arrival_diff minutes later than the first route, and both routes
    arrive by the specified arrival date and time.
    """
    # Get filtered routes
    _, jerusalem_tz, target_arrival = get_routes_data("", "", arrival_date, arrival_time)
    jerusalem_tz = pytz.timezone('Asia/Jerusalem')
    target_arrival_naive = datetime.strptime(f"{arrival_date} {arrival_time}", "%Y-%m-%d %H%M")
    target_arrival = jerusalem_tz.localize(target_arrival_naive)
    
    all_routes = filter_routes_by_arrival(serialized_data, jerusalem_tz, target_arrival)
    
    # Sort routes by departure time for optimization logic
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
    """Legacy handler for optimal departure time (for backward compatibility)"""
    serializable_data, jerusalem_tz, target_arrival = get_routes_data(source, dest, arrival_date, arrival_time)
    
    # Find optimal departure time using serialized data
    all_options = find_optimal_departure_time_from_serialized(serializable_data, arrival_date, arrival_time, max_arrival_diff=10)
    if all_options:
        return all_options[-1]
    return None

if __name__ == "__main__":
    print(israelrailapi)
