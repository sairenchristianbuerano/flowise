import { INode, INodeData, INodeParams, ICommonObject } from 'flowise-components'
import * as moment from 'moment'

class TextProcessor implements INode {
    label: string
    name: string
    version: number
    description: string
    type: string
    icon: string
    category: string
    author: string
    license: string
    baseClasses: string[]
    inputs: INodeParams[]

    constructor() {
        this.label = 'Text Processor'
        this.name = 'textProcessor'
        this.version = 1.0
        this.type = 'TextProcessor'
        this.icon = 'processor'
        this.category = 'Text Processing'
        this.description = 'A component that processes text input and returns formatted output'
        this.author = 'Flowise Team'
        this.license = 'Apache-2.0'
        this.baseClasses = [this.type]
        this.inputs = [
            {
                label: 'Input Text',
                name: 'text',
                type: 'string',
                placeholder: 'Enter text to process...'
            }
        ]
    }

    async init(nodeData: INodeData, _: string, options: ICommonObject): Promise<string> {
        try {
            const inputText = nodeData.inputs?.text as string

            if (!inputText) {
                throw new Error('Input text is required')
            }

            if (typeof inputText !== 'string') {
                throw new Error('Input must be a valid string')
            }

            if (inputText.trim().length === 0) {
                throw new Error('Input text cannot be empty')
            }

            const timestamp = this._formatTimestamp()
            const processedText = this._processText(inputText)

            const result = `${timestamp} ${processedText}`

            return result
        } catch (error) {
            throw new Error(`TextProcessor Error: ${error.message}`)
        }
    }

    private _formatTimestamp(): string {
        return moment().format('YYYY-MM-DD HH:mm:ss')
    }

    private _processText(text: string): string {
        return text.toUpperCase()
    }
}

module.exports = { nodeClass: TextProcessor }
