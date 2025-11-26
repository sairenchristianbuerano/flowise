import { INode, INodeData, INodeParams, ICommonObject } from 'flowise-components'

class DataValidator implements INode {
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
        this.label = 'Data Validator'
        this.name = 'dataValidator'
        this.version = 1.0
        this.type = 'DataValidator'
        this.icon = 'shield-check'
        this.category = 'Data Processing'
        this.description = 'Validates input data against specified rules'
        this.baseClasses = [this.type]
        this.inputs = [
            {
                label: 'Input Data',
                name: 'data',
                type: 'string',
                placeholder: 'Enter data to validate...'
            },
            {
                label: 'Validation Rule',
                name: 'rule',
                type: 'options',
                options: [
                    { label: 'Email', name: 'email' },
                    { label: 'Phone', name: 'phone' },
                    { label: 'URL', name: 'url' },
                    { label: 'Number', name: 'number' }
                ]
            }
        ]
    }

    async init(nodeData: INodeData, _: string, options: ICommonObject): Promise<string> {
        try {
            const data = nodeData.inputs?.data as string
            const rule = nodeData.inputs?.rule as string

            if (!data) {
                throw new Error('Input data is required')
            }

            if (!rule) {
                throw new Error('Validation rule is required')
            }

            const isValid = this._validateData(data, rule)
            const result = {
                data: data,
                rule: rule,
                isValid: isValid,
                message: isValid ? 'Data is valid' : 'Data is invalid'
            }

            return JSON.stringify(result, null, 2)

        } catch (error) {
            throw new Error(`DataValidator Error: ${error.message}`)
        }
    }

    private _validateData(data: string, rule: string): boolean {
        switch (rule) {
            case 'email':
                return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data)
            case 'phone':
                return /^\+?[\d\s\-\(\)]+$/.test(data)
            case 'url':
                try {
                    new URL(data)
                    return true
                } catch {
                    return false
                }
            case 'number':
                return !isNaN(Number(data))
            default:
                return false
        }
    }
}

module.exports = { nodeClass: DataValidator }