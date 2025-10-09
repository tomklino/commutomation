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
          <span v-else>Find Optimal Route</span>
        </button>
      </form>

      <div v-if="loading" class="loading-indicator">
        <p>Searching for the best route...</p>
      </div>

      <div v-if="result && !loading" class="results-container">
        <h2>Optimal Route Found! 🎉</h2>
        <div class="result-card">
          <div class="train-details">
            <div class="train-box">
              <h3>First Train</h3>
              <p><strong>Departure:</strong> {{ formatDate(result.first_route.departure) }}</p>
              <p><strong>Arrival:</strong> {{ formatDate(result.first_route.arrival) }}</p>
              <p><strong>Train Info:</strong> {{ result.first_route.route_info }}</p>
            </div>
            
            <div class="train-box">
              <h3>Backup Train</h3>
              <p><strong>Departure:</strong> {{ formatDate(result.later_route.departure) }}</p>
              <p><strong>Arrival:</strong> {{ formatDate(result.later_route.arrival) }}</p>
              <p><strong>Train Info:</strong> {{ result.later_route.route_info }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!result && !loading && searchAttempted" class="no-results">
        <p>No optimal route found for your criteria. Please try again.</p>
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
const result = ref(null);
const loading = ref(false);
const searchAttempted = ref(false);
const stations = ref([]);
const stationsLoading = ref(false);
const sourceSuggestions = ref([]);
const destSuggestions = ref([]);
const showSourceSuggestions = ref(false);
const showDestSuggestions = ref(false);

// Fetch stations from API
const fetchStations = async () => {
  stationsLoading.value = true;
  try {
    const response = await fetch('/api/stations');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    stations.value = data;
  } catch (error) {
    console.error('Failed to fetch stations:', error);
    stations.value = [];
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
  ).slice(0, 10); // Limit to 10 suggestions
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
  // Set the page title
  document.title = 'Commutomation';
});

const findOptimalRoute = async () => {
  loading.value = true;
  searchAttempted.value = true;
  result.value = null;

  // const backend = process.env.VUE_APP_API_COMMUTOMATION_BACKEND_URL

  const url = `/api/train_route?source=${encodeURIComponent(source.value)}&dest=${encodeURIComponent(dest.value)}&arrival_date=${arrivalDate.value}&arrival_time=${arrivalTime.value.replace(':', '')}`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    result.value = data;
  } catch (error) {
    console.error('Failed to fetch data:', error);
    // You could set an error state here to show a user-friendly message
    result.value = null; 
  } finally {
    loading.value = false;
  }
};

const formatDate = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-IL', { hour: '2-digit', minute: '2-digit' });
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
}

.container {
  background-color: #fff;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 600px;
  text-align: center;
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

h1 {
  color: #4a5568;
  margin: 0;
  font-size: 2rem;
}

form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Responsive layout: on large screens show two inputs per row */
@media (min-width: 900px) {
  form {
    display: grid;
    grid-template-columns: 1fr 1fr;
    column-gap: 3.5rem;
    row-gap: 1.5rem;
    align-items: end;
  }

  /* Make the submit button span both columns */
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
}

.results-container {
  margin-top: 2rem;
  text-align: left;
}

h2 {
  color: #2f855a;
  margin-bottom: 1.5rem;
  text-align: center;
}

.result-card {
  background-color: #edf2f7;
  padding: 1.5rem;
  border-radius: 10px;
}

.result-info p {
  margin: 0.5rem 0;
}

.train-details {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1.5rem;
  text-align: center;
}

.train-box {
  flex: 1;
  background-color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
}

.train-box h3 {
  color: #2d3748;
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.no-results {
  margin-top: 2rem;
  color: #e53e3e;
}
</style>