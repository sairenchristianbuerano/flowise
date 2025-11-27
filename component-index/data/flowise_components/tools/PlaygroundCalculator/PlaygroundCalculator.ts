import { INode, INodeData, INodeParams } from '../../../src/Interface'
import { Tool } from '@langchain/core/tools'
import { handleErrorMessage } from '../../../src/utils'

class PlaygroundCalculator implements INode {
    label: string
    name: string
    version: number
    type: string
    icon: string
    category: string
    description: string
    author: string
    baseClasses: string[]
    inputs: INodeParams[]
    constructor() {
        this.label = 'Playground Calculator'
        this.name = 'playgroundCalculator'
        this.version = 1.0
        this.type = 'PlaygroundCalculator'
        this.icon = 'calculator.svg'
        this.category = 'Tools'
        this.author = 'Flowise Team'
        this.description = 'A flexible mathematical calculator tool that allows performing various mathematical operations'
        this.baseClasses = ['Tool', 'StructuredTool']
        this.inputs = [
            { label: 'Tool Name', name: 'name', type: 'string', default: 'playground_calculator', optional: true },
            { label: 'Tool Description', name: 'description', type: 'string', default: 'Calculator for mathematical expressions and operations', optional: true },
            { label: 'Math Function Mode', name: 'mathFunction', type: 'options', options: [{ label: 'Default (Expression Evaluation)', name: 'default' }, { label: 'Addition', name: 'add' }, { label: 'Subtraction', name: 'subtract' }, { label: 'Multiplication', name: 'multiply' }, { label: 'Division', name: 'divide' }, { label: 'Power', name: 'power' }, { label: 'Square Root', name: 'sqrt' }, { label: 'Sine', name: 'sin' }, { label: 'Cosine', name: 'cos' }, { label: 'Tangent', name: 'tan' }], default: 'default', optional: true }
        ]
    }

    async init(nodeData: INodeData): Promise<Tool> {
        try {
            const name = nodeData.inputs?.name as string
            const description = nodeData.inputs?.description as string
            const mathFunction = nodeData.inputs?.mathFunction as string
            if (name && typeof name !== 'string') {
                throw new Error('Tool name must be a string')
            }
            if (description && typeof description !== 'string') {
                throw new Error('Tool description must be a string')
            }
            const tool = new PlaygroundCalculatorCustomTool({
                name: name || 'playground_calculator',
                description: description || 'Calculator for mathematical expressions and operations',
                mathFunction: mathFunction || 'default'
            })
            return tool
        } catch (error) {
            throw new Error(`Failed to initialize Playground Calculator: ${handleErrorMessage(error)}`)
        }
    }
}

class PlaygroundCalculatorCustomTool extends Tool {
    name: string
    description: string
    mathFunction: string
    constructor(fields: { name: string; description: string; mathFunction: string }) {
        super()
        this.name = fields.name
        this.description = fields.description
        this.mathFunction = fields.mathFunction
    }

    private _sanitizeExpression(expression: string): string {
        const sanitized = expression.trim()
        if (sanitized.includes('<script') || sanitized.includes('javascript:') || sanitized.includes('eval')) {
            throw new Error('Invalid expression - potential security risk detected')
        }
        return sanitized
    }

    private _validateMathExpression(expression: string): boolean {
        if (!expression || typeof expression !== 'string') {
            return false
        }
        const allowedPattern = /^[0-9+\-*/().\s]+$/
        return allowedPattern.test(expression)
    }

    private _convertDegreesToRadians(degrees: number): number {
        return degrees * (Math.PI / 180)
    }

    private _applyMathFunction(input: string, functionType: string): number {
        const parts = input.split(',').map(part => parseFloat(part.trim()))

        switch (functionType) {
            case 'add':
                if (parts.length < 2) throw new Error('Addition requires at least 2 numbers separated by comma')
                return parts.reduce((sum, num) => sum + num, 0)

            case 'subtract':
                if (parts.length !== 2) throw new Error('Subtraction requires exactly 2 numbers separated by comma')
                return parts[0] - parts[1]

            case 'multiply':
                if (parts.length < 2) throw new Error('Multiplication requires at least 2 numbers separated by comma')
                return parts.reduce((product, num) => product * num, 1)

            case 'divide':
                if (parts.length !== 2) throw new Error('Division requires exactly 2 numbers separated by comma')
                if (parts[1] === 0) throw new Error('Division by zero is not allowed')
                return parts[0] / parts[1]

            case 'power':
                if (parts.length !== 2) throw new Error('Power requires exactly 2 numbers separated by comma (base, exponent)')
                return Math.pow(parts[0], parts[1])

            case 'sqrt':
                if (parts.length !== 1) throw new Error('Square root requires exactly 1 number')
                if (parts[0] < 0) throw new Error('Square root of negative number is not supported')
                return Math.sqrt(parts[0])

            case 'sin':
                if (parts.length !== 1) throw new Error('Sine requires exactly 1 number (in degrees)')
                return Math.sin(this._convertDegreesToRadians(parts[0]))

            case 'cos':
                if (parts.length !== 1) throw new Error('Cosine requires exactly 1 number (in degrees)')
                return Math.cos(this._convertDegreesToRadians(parts[0]))

            case 'tan':
                if (parts.length !== 1) throw new Error('Tangent requires exactly 1 number (in degrees)')
                return Math.tan(this._convertDegreesToRadians(parts[0]))

            default:
                throw new Error(`Unknown math function: ${functionType}`)
        }
    }

    private _evaluateSafeExpression(expression: string): number {
        const cleanExpression = expression
            .replace(/sin\(([^)]+)\)/g, (match, angle) => `Math.sin(${parseFloat(angle)} * Math.PI / 180)`)
            .replace(/cos\(([^)]+)\)/g, (match, angle) => `Math.cos(${parseFloat(angle)} * Math.PI / 180)`)
            .replace(/tan\(([^)]+)\)/g, (match, angle) => `Math.tan(${parseFloat(angle)} * Math.PI / 180)`)
            .replace(/sqrt\(([^)]+)\)/g, 'Math.sqrt($1)')
            .replace(/pow\(([^]+),([^)]+)\)/g, 'Math.pow($1,$2)')
            .replace(/abs\(([^)]+)\)/g, 'Math.abs($1)')
            .replace(/floor\(([^)]+)\)/g, 'Math.floor($1)')
            .replace(/ceil\(([^)]+)\)/g, 'Math.ceil($1)')
        if (!/^[0-9+\-*/().\sMath]+$/.test(cleanExpression)) {
            throw new Error('Expression contains invalid characters after processing')
        }

        try {
            const result = eval(cleanExpression)
            if (typeof result !== 'number' || !isFinite(result)) {
                throw new Error('Expression did not evaluate to a valid number')
            }
            return result
        } catch (error) {
            throw new Error(`Expression evaluation failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
        }
    }

    private _formatResult(result: number): string {
        if (Number.isInteger(result)) {
            return result.toString()
        }
        const rounded = Math.round(result * 1000000) / 1000000
        return rounded.toString()
    }

    async _call(input: string): Promise<string> {
        try {
            if (!input || typeof input !== 'string') {
                throw new Error('Input must be a non-empty string')
            }
            const sanitized = this._sanitizeExpression(input)
            if (sanitized.length === 0) {
                throw new Error('Input cannot be empty after sanitization')
            }
            let result: number
            if (this.mathFunction === 'default') {
                if (!this._validateMathExpression(sanitized)) {
                    throw new Error('Invalid mathematical expression format')
                }
                result = this._evaluateSafeExpression(sanitized)
            } else {
                result = this._applyMathFunction(sanitized, this.mathFunction)
            }
            return this._formatResult(result)
        } catch (error) {
            throw new Error(`Calculator error: ${handleErrorMessage(error)}`)
        }
    }
}

module.exports = { nodeClass: PlaygroundCalculator }
