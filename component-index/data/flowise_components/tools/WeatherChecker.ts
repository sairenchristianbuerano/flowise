import { INode, INodeData, INodeParams, ICommonObject } from 'flowise-components'
import axios from 'axios'

class WeatherChecker implements INode {
    label: string
    name: string
    version: number
    description: string
    type: string
    icon: string
    category: string
    baseClasses: string[]
    inputs: INodeParams[]

    constructor() {
        this.label = 'Weather Checker'
        this.name = 'weatherChecker'
        this.version = 1.0
        this.type = 'WeatherChecker'
        this.icon = 'cloud'
        this.category = 'External APIs'
        this.description = 'Checks weather information for a given city'
        this.baseClasses = [this.type]
        this.inputs = [
            {
                label: 'City',
                name: 'city',
                type: 'string',
                placeholder: 'Enter city name...'
            },
            {
                label: 'API Key',
                name: 'apiKey',
                type: 'password',
                placeholder: 'Enter weather API key...'
            }
        ]
    }

    async init(nodeData: INodeData, _: string, options: ICommonObject): Promise<string> {
        try {
            const city = nodeData.inputs?.city as string
            const apiKey = nodeData.inputs?.apiKey as string

            if (!city) {
                throw new Error('City name is required')
            }

            if (!apiKey) {
                throw new Error('API key is required')
            }

            const response = await axios.get(
                `https://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${apiKey}&units=metric`
            )

            const weather = response.data
            const result = `Weather in ${weather.name}: ${weather.weather[0].description}, ${weather.main.temp}°C`

            return result

        } catch (error) {
            throw new Error(`WeatherChecker Error: ${error.message}`)
        }
    }
}

module.exports = { nodeClass: WeatherChecker }