# Weather Checker Tool

A custom Flowise component that fetches current weather information using the OpenWeatherMap API.

## Features

- Get current weather for any city worldwide
- Support for multiple temperature units (Celsius, Fahrenheit, Kelvin)
- Optional extended weather information (humidity, wind speed, pressure)
- Configurable default city
- Error handling for invalid cities and API issues
- Formatted output with emojis for better readability

## Setup

### 1. Get OpenWeatherMap API Key

1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Generate an API key from your account dashboard

### 2. Configure Credentials in Flowise

1. Go to Settings → Credentials
2. Click "Add Credential"
3. Select "Weather API" 
4. Enter your OpenWeatherMap API key
5. Save the credential

### 3. Add Weather Checker to Your Flow

1. In the Flowise canvas, look for "Weather Checker" in the Tools category
2. Connect your Weather API credential
3. Configure the tool parameters as needed

## Configuration Options

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| Default City | String | Default city to check weather for | None |
| Temperature Unit | Options | Celsius, Fahrenheit, or Kelvin | Celsius |
| Include Extended Info | Boolean | Include humidity, wind, and pressure | True |

## Usage Examples

### Basic Usage
When connected to an agent or chatflow, the tool can be called with:

```
What's the weather in London?
```

### With Country Code (Recommended)
For better accuracy, include the country code:

```
Check the weather in London,UK
```

### Multiple Cities
```
What's the weather in New York,US and Tokyo,JP?
```

## Output Format

The tool returns formatted weather information like:

```
🌤️ **Weather in London, GB**
🌡️ Temperature: 15°C (feels like 13°C)
☁️ Conditions: Partly cloudy
💧 Humidity: 72%
💨 Wind Speed: 3.5 m/s
🔽 Pressure: 1013 hPa
```

## Error Handling

The tool handles various error scenarios:

- **City not found**: "City 'XYZ' not found. Please check the spelling and try again."
- **Invalid API key**: "Invalid API key. Please check your OpenWeatherMap API credentials."
- **Network timeout**: "Weather API request timed out. Please try again."
- **General errors**: Descriptive error messages for troubleshooting

## API Rate Limits

OpenWeatherMap free tier includes:
- 1,000 API calls per day
- 60 calls per minute

For higher usage, consider upgrading to a paid plan.

## Troubleshooting

### Common Issues

1. **"API key required" error**
   - Ensure you've created and connected the Weather API credential
   - Verify your API key is correct in the credential settings

2. **"City not found" errors**
   - Check spelling of city names
   - Use city names in English
   - Include country codes for better accuracy (e.g., "Paris,FR" vs "Paris,US")

3. **Timeout or connection errors**
   - Check your internet connection
   - Verify OpenWeatherMap service status
   - Try again after a few moments

### Best Practices

1. **Use country codes** for cities with common names (e.g., "Springfield,US" vs "Springfield,AU")
2. **Set a default city** if your use case typically queries the same location
3. **Enable extended info** for comprehensive weather reports
4. **Monitor API usage** to stay within rate limits

## Development Notes

This component demonstrates several Flowise custom component patterns:

- **Credential integration** for secure API key storage
- **Input validation** and error handling
- **External API calls** with proper timeout handling
- **Formatted output** with emojis and structured text
- **Conditional parameters** (extended info based on configuration)
- **Tool schema definition** for LLM integration