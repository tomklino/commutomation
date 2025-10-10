<template>
  <div id="app">
    <div class="container">
      <div class="header">
        <img src="./assets/commutomation-circular-logo.webp" alt="Commutomation Logo" class="logo" />
      </div>
      
      <form @submit.prevent="findOptimalRoute">
        <div class="input-group">
          <label for="source">Source Station:</label>
          <div class="autocomplete-container">
            <input
              id="source" 
              v-model="source" 
              @input="handleSourceInput"
              @focus="handleSourceInput"
              @blur="handleSourceBlur"
              autocomplete="off"
              required 
            />
            <div v-if="showSourceSuggestions && sourceSuggestions.length > 0" class="autocomplete-dropdown">
              <div 
                v-for="station in sourceSuggestions" 
                :key="station"
                @click="selectSourceStation(station)"
                class="autocomplete-item"
              >
                {{ station }}
              </div>
            </div>
          </div>
        </div>
        <div class="input-group">
          <label for="dest">Destination Station:</label>
          <div class="autocomplete-container">
            <input 
              id="dest" 
              v-model="dest" 
              @input="handleDestInput"
              @focus="handleDestInput"
              @blur="handleDestBlur"
              autocomplete="off"
              required 
            />
            <div v-if="showDestSuggestions && destSuggestions.length > 0" class="autocomplete-dropdown">
              <div 
                v-for="station in destSuggestions" 
                :key="station"
                @click="selectDestStation(station)"
                class="autocomplete-item"
              >
                {{ station }}
              </div>
            </div>
          </div>
        </div>
        <div class="input-group">
          <label for="arrival-date">Arrival Date:</label>
          <input id="arrival-date" type="date" v-model="arrivalDate" required />
        </div>
        <div class="input-group">
          <label for="arrival-time">Arrival Time:</label>
          <input id="arrival-time" type="time" v-model="arrivalTime" required />
        </div>
        <button type="submit" :disabled="loading">
          <span v-if="loading">Searching...</span>
          <span v-else>Find Routes</span>
        </button>
      </form>

      <div v-if="loading" class="loading-indicator">
        <p>Searching for the best routes...</p>
      </div>

      <div v-if="routes && routes.length > 0 && !loading" class="results-container">
        <h2>Available Routes 🚆</h2>
        
        <div 
          v-for="routeItem in routes" 
          :key="routeItem.route.route_id" 
          :ref="el => setRouteRef(routeItem.route.route_id, el)"
          class="route-card"
        >
          <div class="route-header">
            <div class="arrival-time">
              <div class="arrival-label">Arrives at</div>
              <div class="arrival-value">{{ formatTime(routeItem.route.endTime) }}</div>
            </div>
          </div>
          
          <div class="route-details">
            <div class="time-info">
              <span class="label">Departs:</span>
              <span class="value">{{ formatTime(routeItem.route.startTime) }}</span>
            </div>
            <div class="time-info">
              <span class="label">Duration:</span>
              <span class="value">{{ calculateDuration(routeItem.route.startTime, routeItem.route.endTime) }}</span>
            </div>
            <div class="time-info">
              <span class="label">Transfers:</span>
              <span class="value">{{ routeItem.route.trains.length - 1 }}</span>
            </div>
          </div>

          <div class="trains-section">
            <h4>Train Details:</h4>
            <div v-for="(train, trainIndex) in routeItem.route.trains" :key="trainIndex" class="train-item">
              <div class="train-number-badge">Train {{ train.trainNumber }}</div>
              <div class="train-info">
                <div class="train-route">
                  <span class="station-name">{{ resolveStationName(train.originStation) }}</span>
                  <span class="arrow">→</span>
                  <span class="station-name">{{ resolveStationName(train.destinationStation) }}</span>
                </div>
                <div class="train-times">
                  <span>{{ formatTime(train.departure) }} → {{ formatTime(train.arrival) }}</span>
                  <span v-if="train.platformNumber" class="platform">Platform {{ train.platformNumber }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="routeItem.route.backupRoutes && routeItem.route.backupRoutes.length > 0" class="backup-section">
            <h4>Backup Routes:</h4>
            <div 
              v-for="backup in routeItem.route.backupRoutes" 
              :key="backup.route_id" 
              @click="scrollToRoute(backup.route_id)"
              class="backup-item"
            >
              <div class="backup-main-info">
                <span class="backup-time">{{ formatTime(getRouteById(backup.route_id).startTime) }}</span>
                <span class="backup-delay">+{{ Math.round(backup.delayMinutes) }} min</span>
              </div>
              <div class="backup-platform" v-if="getFirstPlatform(backup.route_id)">
                Platform {{ getFirstPlatform(backup.route_id) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!routes && !loading && searchAttempted" class="no-results">
        <p>No routes found for your criteria. Please try different search parameters.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const source = ref('');
const dest = ref('');
const arrivalDate = ref('');
const arrivalTime = ref('');
const routes = ref(null);
const loading = ref(false);
const searchAttempted = ref(false);
const stations = ref([]);
const stationMap = ref({});
const stationsLoading = ref(false);
const sourceSuggestions = ref([]);
const destSuggestions = ref([]);
const showSourceSuggestions = ref(false);
const showDestSuggestions = ref(false);
const routeRefs = ref({});

// Set route ref for scrolling
const setRouteRef = (routeId, el) => {
  if (el) {
    routeRefs.value[routeId] = el;
  }
};

// Scroll to a specific route
const scrollToRoute = (routeId) => {
  const element = routeRefs.value[routeId];
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    // Add a highlight effect
    element.classList.add('highlight');
    setTimeout(() => {
      element.classList.remove('highlight');
    }, 2000);
  }
};

// Get route by ID
const getRouteById = (routeId) => {
  const found = routes.value.find(r => r.route.route_id === routeId);
  return found ? found.route : null;
};

// Get first platform number for a route
const getFirstPlatform = (routeId) => {
  const route = getRouteById(routeId);
  if (route && route.trains && route.trains.length > 0) {
    return route.trains[0].platformNumber;
  }
  return null;
};

// Resolve station ID to name
const resolveStationName = (stationId) => {
  if (!stationId) return 'Unknown';
  
  // If it's already a string name (not a number), return it
  if (typeof stationId === 'string' && !stationId.match(/^\d+$/)) {
    return stationId;
  }
  
  // Convert to string for lookup
  const idStr = String(stationId);
  
  // Look up in station map
  if (stationMap.value[idStr]) {
    return stationMap.value[idStr];
  }
  
  // If not found, return the original value
  return stationId;
};

// Fetch stations from API
const fetchStations = async () => {
  stationsLoading.value = true;
  try {
    // Fetch station list for autocomplete
    const listResponse = await fetch('/api/stations');
    if (!listResponse.ok) {
      throw new Error(`HTTP error! Status: ${listResponse.status}`);
    }
    const listData = await listResponse.json();
    stations.value = listData;
    
    // Fetch station map for ID resolution
    const mapResponse = await fetch('/api/stations?format=map');
    if (!mapResponse.ok) {
      throw new Error(`HTTP error! Status: ${mapResponse.status}`);
    }
    const mapData = await mapResponse.json();
    stationMap.value = mapData;
  } catch (error) {
    console.error('Failed to fetch stations:', error);
    stations.value = [];
    stationMap.value = {};
  } finally {
    stationsLoading.value = false;
  }
};

// Filter stations based on input
const filterStations = (input, suggestions) => {
  if (!input || input.length < 1) {
    suggestions.value = [];
    return;
  }
  suggestions.value = stations.value.filter(station => 
    station.toLowerCase().includes(input.toLowerCase())
  ).slice(0, 10);
};

// Handle source input changes
const handleSourceInput = () => {
  filterStations(source.value, sourceSuggestions);
  showSourceSuggestions.value = sourceSuggestions.value.length > 0;
};

// Handle destination input changes
const handleDestInput = () => {
  filterStations(dest.value, destSuggestions);
  showDestSuggestions.value = destSuggestions.value.length > 0;
};

// Select suggestion
const selectSourceStation = (station) => {
  source.value = station;
  showSourceSuggestions.value = false;
  sourceSuggestions.value = [];
};

const selectDestStation = (station) => {
  dest.value = station;
  showDestSuggestions.value = false;
  destSuggestions.value = [];
};

// Handle blur events with delay
const handleSourceBlur = () => {
  setTimeout(() => {
    showSourceSuggestions.value = false;
  }, 200);
};

const handleDestBlur = () => {
  setTimeout(() => {
    showDestSuggestions.value = false;
  }, 200);
};

// Load stations on component mount
onMounted(() => {
  fetchStations();
  document.title = 'Commutomation';
});

const findOptimalRoute = async () => {
  loading.value = true;
  searchAttempted.value = true;
  routes.value = null;

  const url = `/api/v1/train_route?source=${encodeURIComponent(source.value)}&dest=${encodeURIComponent(dest.value)}&arrival_date=${arrivalDate.value}&arrival_time=${arrivalTime.value.replace(':', '')}`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    routes.value = data;
  } catch (error) {
    console.error('Failed to fetch data:', error);
    routes.value = null; 
  } finally {
    loading.value = false;
  }
};

const formatTime = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-IL', { hour: '2-digit', minute: '2-digit' });
};

const calculateDuration = (startTime, endTime) => {
  const start = new Date(startTime);
  const end = new Date(endTime);
  const diffMs = end - start;
  const diffMins = Math.round(diffMs / 60000);
  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  
  if (hours > 0) {
    return `${hours}h ${mins}m`;
  }
  return `${mins}m`;
};

</script>

<style scoped>
#app {
  font-family: Arial, sans-serif;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f0f2f5;
  color: #333;
  padding: 2rem 1rem;
}

.container {
  background-color: #fff;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 800px;
}

.header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 2rem;
}

.logo {
  height: 400px;
  width: auto;
  display: block;
  margin: 0 auto 1rem;
  object-fit: contain;
}

form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media (min-width: 900px) {
  form {
    display: grid;
    grid-template-columns: 1fr 1fr;
    column-gap: 3.5rem;
    row-gap: 1.5rem;
    align-items: end;
  }

  form > button {
    grid-column: 1 / -1;
    justify-self: stretch;
  }
}

.input-group {
  text-align: left;
}

.input-group label {
  display: block;
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #2d3748;
}

.input-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
}

.autocomplete-container {
  position: relative;
}

.autocomplete-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e2e8f0;
  border-top: none;
  border-radius: 0 0 8px 8px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.autocomplete-item {
  padding: 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid #f7fafc;
  transition: background-color 0.2s;
}

.autocomplete-item:hover {
  background-color: #f7fafc;
}

.autocomplete-item:last-child {
  border-bottom: none;
}

button {
  padding: 1rem;
  background-color: #4299e1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

button:hover:enabled {
  background-color: #2b6cb0;
}

button:disabled {
  background-color: #a0aec0;
  cursor: not-allowed;
}

.loading-indicator {
  margin-top: 2rem;
  color: #718096;
  text-align: center;
}

.results-container {
  margin-top: 2rem;
}

h2 {
  color: #2d3748;
  margin-bottom: 1.5rem;
  text-align: center;
  font-size: 1.8rem;
}

.route-card {
  background-color: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  transition: box-shadow 0.2s;
}

.route-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.route-header {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #edf2f7;
}

.route-number {
  font-weight: bold;
  color: #4299e1;
  font-size: 1.1rem;
}

.arrival-time {
  text-align: center;
}

.arrival-label {
  font-size: 0.85rem;
  color: #718096;
  margin-bottom: 0.25rem;
}

.arrival-value {
  font-size: 2rem;
  font-weight: bold;
  color: #2f855a;
}

.route-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #f7fafc;
  border-radius: 8px;
}

.time-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.time-info .label {
  font-size: 0.85rem;
  color: #718096;
}

.time-info .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #2d3748;
}

.trains-section {
  margin-bottom: 1rem;
}

.trains-section h4 {
  color: #2d3748;
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.train-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background-color: #edf2f7;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.train-number-badge {
  background-color: #4299e1;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.9rem;
  white-space: nowrap;
}

.train-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.train-route {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #2d3748;
}

.station-name {
  font-size: 1rem;
}

.arrow {
  color: #4299e1;
  font-weight: bold;
}

.train-times {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.95rem;
  color: #4a5568;
}

.platform {
  color: #718096;
  font-size: 0.9rem;
  white-space: nowrap;
}

.backup-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.backup-section h4 {
  color: #2d3748;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
}

.backup-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background-color: #fef5e7;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  border-left: 3px solid #f6ad55;
  cursor: pointer;
  transition: all 0.2s;
}

.backup-item:hover {
  background-color: #fde68a;
  transform: translateX(4px);
}

.backup-main-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.backup-time {
  font-weight: 600;
  color: #744210;
  font-size: 1.1rem;
}

.backup-delay {
  color: #c05621;
  font-size: 0.9rem;
}

.backup-platform {
  color: #744210;
  font-size: 0.9rem;
}

.route-card.highlight {
  animation: highlight-pulse 2s ease-in-out;
}

@keyframes highlight-pulse {
  0%, 100% {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  50% {
    box-shadow: 0 0 20px rgba(66, 153, 225, 0.6);
    transform: scale(1.02);
  }
}

.no-results {
  margin-top: 2rem;
  text-align: center;
  color: #e53e3e;
  padding: 2rem;
  background-color: #fff5f5;
  border-radius: 8px;
  border: 1px solid #feb2b2;
}
</style>