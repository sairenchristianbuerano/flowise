"""
Flowise RAG Engine

Semantic search and pattern extraction for Flowise component templates.
Indexes Flowise component patterns and provides intelligent component suggestions.
"""

import os
import json
import glob
from typing import List, Dict, Any, Optional
import structlog
import chromadb
from chromadb.config import Settings

logger = structlog.get_logger()


class FlowiseRAGEngine:
    """RAG engine for Flowise component patterns and templates"""

    def __init__(
        self,
        flowise_components_dir: str = "data/flowise_components",
        persist_directory: str = "data/chromadb"
    ):
        self.components_dir = flowise_components_dir
        self.persist_directory = persist_directory
        self.collection_name = "flowise_components"
        
        self.logger = logger.bind(engine="flowise_rag")
        
        # Initialize ChromaDB
        self._init_chromadb()
        
    def _init_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection for Flowise components
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Flowise component patterns and templates"}
            )
            
            self.logger.info(
                "ChromaDB initialized for Flowise components",
                collection=self.collection_name,
                persist_dir=self.persist_directory
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize ChromaDB", error=str(e))
            raise

    def index_components(self, force_reindex: bool = False) -> int:
        """
        Index all Flowise components from the components directory.
        
        Args:
            force_reindex: Whether to clear existing index and rebuild
            
        Returns:
            Number of components indexed
        """
        self.logger.info(
            "Starting Flowise component indexing",
            components_dir=self.components_dir,
            force_reindex=force_reindex
        )
        
        # Clear existing if force reindex
        if force_reindex:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Flowise component patterns and templates"}
                )
                self.logger.info("Cleared existing Flowise component index")
            except Exception as e:
                self.logger.warning("Failed to clear collection", error=str(e))

        # Ensure components directory exists
        os.makedirs(self.components_dir, exist_ok=True)
        
        # Find all Flowise component files (TypeScript components)
        pattern = os.path.join(self.components_dir, "**", "*.ts")
        component_files = glob.glob(pattern, recursive=True)
        
        if not component_files:
            self.logger.warning(
                "No Flowise component files found",
                pattern=pattern,
                components_dir=self.components_dir
            )
            return 0

        indexed_count = 0
        
        for file_path in component_files:
            try:
                component_data = self._load_component_file(file_path)
                if component_data:
                    self._index_single_component(component_data, file_path)
                    indexed_count += 1
                    
            except Exception as e:
                self.logger.error(
                    "Failed to index component",
                    file_path=file_path,
                    error=str(e)
                )
                continue

        self.logger.info(
            "Flowise component indexing completed",
            indexed_count=indexed_count,
            total_files=len(component_files)
        )
        
        return indexed_count

    def _load_component_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load and validate a Flowise TypeScript component file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                typescript_code = f.read()
                
            # Parse TypeScript component into structured data
            component_data = self._parse_typescript_component(typescript_code, file_path)
            
            # Basic validation for Flowise component structure
            if not self._is_valid_flowise_component(component_data):
                self.logger.warning(
                    "Invalid Flowise component structure",
                    file_path=file_path
                )
                return None
                
            return component_data
            
        except (FileNotFoundError, UnicodeDecodeError) as e:
            self.logger.error(
                "Failed to load component file",
                file_path=file_path,
                error=str(e)
            )
            return None

    def _parse_typescript_component(self, typescript_code: str, file_path: str) -> Dict[str, Any]:
        """Parse TypeScript component code into structured data"""
        import re
        
        component_data = {
            'name': '',
            'label': '',
            'description': '',
            'category': '',
            'version': '1.0',
            'inputs': [],
            'code': typescript_code,
            'file_path': file_path
        }
        
        # Extract class name
        class_match = re.search(r'class\s+(\w+)\s+implements\s+INode', typescript_code)
        if class_match:
            component_data['name'] = class_match.group(1)
        
        # Extract label from constructor
        label_match = re.search(r'this\.label\s*=\s*[\'"`]([^\'"`]+)[\'"`]', typescript_code)
        if label_match:
            component_data['label'] = label_match.group(1)
        
        # Extract description from constructor
        desc_match = re.search(r'this\.description\s*=\s*[\'"`]([^\'"`]+)[\'"`]', typescript_code)
        if desc_match:
            component_data['description'] = desc_match.group(1)
        
        # Extract category from constructor
        category_match = re.search(r'this\.category\s*=\s*[\'"`]([^\'"`]+)[\'"`]', typescript_code)
        if category_match:
            component_data['category'] = category_match.group(1)
        
        # Extract version from constructor
        version_match = re.search(r'this\.version\s*=\s*([0-9.]+)', typescript_code)
        if version_match:
            component_data['version'] = version_match.group(1)
        
        # Extract inputs from constructor
        inputs_match = re.search(r'this\.inputs\s*=\s*\[(.*?)\]', typescript_code, re.DOTALL)
        if inputs_match:
            inputs_text = inputs_match.group(1)
            component_data['inputs'] = self._parse_typescript_inputs(inputs_text)
        
        return component_data
    
    def _parse_typescript_inputs(self, inputs_text: str) -> list:
        """Parse TypeScript inputs array"""
        import re
        
        inputs = []
        
        # Find all input objects in the array
        input_pattern = r'\{([^}]+)\}'
        input_matches = re.findall(input_pattern, inputs_text)
        
        for input_match in input_matches:
            input_obj = {}
            
            # Extract name
            name_match = re.search(r'name:\s*[\'"`]([^\'"`]+)[\'"`]', input_match)
            if name_match:
                input_obj['name'] = name_match.group(1)
            
            # Extract label
            label_match = re.search(r'label:\s*[\'"`]([^\'"`]+)[\'"`]', input_match)
            if label_match:
                input_obj['label'] = label_match.group(1)
            
            # Extract type
            type_match = re.search(r'type:\s*[\'"`]([^\'"`]+)[\'"`]', input_match)
            if type_match:
                input_obj['type'] = type_match.group(1)
            
            # Extract required
            required_match = re.search(r'required:\s*(true|false)', input_match)
            if required_match:
                input_obj['required'] = required_match.group(1) == 'true'
            
            if input_obj:
                inputs.append(input_obj)
        
        return inputs

    def _is_valid_flowise_component(self, data: Dict[str, Any]) -> bool:
        """Check if data represents a valid Flowise component"""
        required_fields = ['name', 'label']
        
        # Check if it has basic Flowise component structure
        # For TypeScript components, check direct fields
        return all(field in data and data[field] for field in required_fields)

    def _index_single_component(self, component_data: Dict[str, Any], file_path: str):
        """Index a single Flowise component"""
        
        # Extract component information
        component_info = self._extract_component_info(component_data)
        
        # Create searchable document text
        document_text = self._create_document_text(component_info)
        
        # Generate component ID
        component_id = component_info.get('name', os.path.basename(file_path))
        
        # Prepare metadata
        metadata = self._create_metadata(component_info, file_path)
        
        try:
            # Add to ChromaDB
            self.collection.add(
                documents=[document_text],
                metadatas=[metadata],
                ids=[component_id]
            )
            
            self.logger.debug(
                "Indexed Flowise component",
                component_id=component_id,
                component_name=component_info.get('label'),
                category=component_info.get('category')
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to add component to collection",
                component_id=component_id,
                error=str(e)
            )
            raise

    def _extract_component_info(self, component_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from Flowise component data"""
        
        # For TypeScript components, data is directly accessible
        info = {
            'name': component_data.get('name', ''),
            'label': component_data.get('label', ''),
            'description': component_data.get('description', ''),
            'category': component_data.get('category', 'custom'),
            'version': component_data.get('version', '1.0'),
            'inputs': component_data.get('inputs', []),
            'outputs': [],
            'code': component_data.get('code', ''),
            'imports': [],
            'dependencies': []
        }
        
        # Extract imports from code
        if info['code']:
            info['imports'] = self._extract_imports(info['code'])
            
        return info

    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements from TypeScript/JavaScript code"""
        imports = []
        
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('const ') and 'require(' in line:
                imports.append(line)
                
        return imports[:10]  # Limit to first 10 imports

    def _create_document_text(self, component_info: Dict[str, Any]) -> str:
        """Create searchable document text for semantic search"""
        
        # Build comprehensive searchable text
        text_parts = []
        
        # Basic info
        text_parts.append(f"Component: {component_info['name']}")
        text_parts.append(f"Label: {component_info['label']}")
        text_parts.append(f"Description: {component_info['description']}")
        text_parts.append(f"Category: {component_info['category']}")
        
        # Input information
        if component_info['inputs']:
            input_types = [inp['type'] for inp in component_info['inputs']]
            input_names = [inp['name'] for inp in component_info['inputs']]
            text_parts.append(f"Input Types: {', '.join(set(input_types))}")
            text_parts.append(f"Input Names: {', '.join(input_names)}")
            
        # Code information
        if component_info['code']:
            code_lines = len(component_info['code'].split('\n'))
            text_parts.append(f"Lines of Code: {code_lines}")
            
            # Add method names from code
            methods = self._extract_method_names(component_info['code'])
            if methods:
                text_parts.append(f"Methods: {', '.join(methods)}")
                
        # Join all parts
        return " | ".join(text_parts)

    def _extract_method_names(self, code: str) -> List[str]:
        """Extract method names from TypeScript code"""
        import re
        
        methods = []
        
        # Find async methods
        async_pattern = r'async\s+(\w+)\s*\('
        methods.extend(re.findall(async_pattern, code))
        
        # Find regular methods
        method_pattern = r'(\w+)\s*\([^)]*\)\s*:\s*\w+'
        methods.extend(re.findall(method_pattern, code))
        
        return list(set(methods))[:5]  # Limit and deduplicate

    def _create_metadata(self, component_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Create metadata for ChromaDB storage"""
        
        metadata = {
            'name': component_info['name'],
            'label': component_info['label'],
            'description': component_info['description'][:500],  # Limit description length
            'category': component_info['category'],
            'version': str(component_info['version']),
            'file_path': file_path,
            'platform': 'flowise',
            'inputs_count': len(component_info['inputs']),
            'code_lines': len(component_info['code'].split('\n')) if component_info['code'] else 0,
            'has_code': bool(component_info['code'])
        }
        
        # Add input types as comma-separated string
        if component_info['inputs']:
            input_types = [inp['type'] for inp in component_info['inputs']]
            metadata['input_types'] = ','.join(set(input_types))
            
        return metadata

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for Flowise components using semantic search
        
        Args:
            query: Natural language search query
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of matching components with similarity scores
        """
        self.logger.info(
            "Flowise component search",
            query=query[:100],
            n_results=n_results,
            filters=filters
        )
        
        try:
            # Prepare where clause for filtering
            where_clause = {'platform': 'flowise'}
            
            if filters:
                # Use $and operator for multiple conditions
                conditions = [{'platform': 'flowise'}]
                for key, value in filters.items():
                    conditions.append({key: value})
                where_clause = {'$and': conditions}
            else:
                where_clause = {'platform': 'flowise'}
            
            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = self._format_search_results(results)
            
            self.logger.info(
                "Flowise search completed",
                results_count=len(formatted_results)
            )
            
            return formatted_results
            
        except Exception as e:
            self.logger.error("Flowise component search failed", error=str(e))
            raise

    def find_similar_components(
        self,
        description: str,
        category: Optional[str] = None,
        input_types: Optional[List[str]] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar Flowise components based on description and requirements
        
        Args:
            description: Component description
            category: Optional category filter
            input_types: Optional input type requirements
            n_results: Number of results to return
            
        Returns:
            List of similar components with extracted patterns
        """
        self.logger.info(
            "Finding similar Flowise components",
            description=description[:100],
            category=category,
            input_types=input_types
        )
        
        # Build enhanced query
        query_parts = [description]
        
        if category:
            query_parts.append(f"category: {category}")
            
        if input_types:
            query_parts.append(f"input types: {', '.join(input_types)}")
            
        enhanced_query = " | ".join(query_parts)
        
        # Build filters
        filters = {'platform': 'flowise'}
        if category:
            filters['category'] = category
            
        # Search for similar components
        results = self.search(
            query=enhanced_query,
            n_results=n_results,
            filters=filters
        )
        
        # Enhance results with pattern information
        enhanced_results = []
        for result in results:
            enhanced_result = result.copy()
            
            # Add pattern extraction
            enhanced_result.update(self._extract_component_patterns(result))
            enhanced_results.append(enhanced_result)
            
        return enhanced_results

    def _extract_component_patterns(self, component_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract reusable patterns from a component result"""
        
        patterns = {
            'input_patterns': [],
            'imports': [],
            'code_snippets': []
        }
        
        # Extract input patterns
        if 'inputs' in component_result:
            for inp in component_result['inputs']:
                patterns['input_patterns'].append({
                    'name': inp.get('name'),
                    'label': inp.get('label'),
                    'type': inp.get('type'),
                    'required': inp.get('required', False)
                })
                
        # Extract imports if available in metadata
        if 'imports' in component_result:
            patterns['imports'] = component_result['imports']
            
        # Add code snippet if available
        if component_result.get('code'):
            code_lines = component_result['code'].split('\n')
            snippet = '\n'.join(code_lines[:30])  # First 30 lines
            patterns['code_snippets'].append({
                'source': component_result.get('name'),
                'snippet': snippet
            })
            
        return patterns

    def _format_search_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format ChromaDB search results"""
        
        formatted_results = []
        
        if not results['documents'] or not results['documents'][0]:
            return formatted_results
            
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        ids = results['ids'][0] if results['ids'] else []
        
        for i, doc in enumerate(documents):
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            component_id = ids[i] if i < len(ids) else f"component_{i}"
            
            result = {
                'component_id': component_id,
                'name': metadata.get('name', ''),
                'label': metadata.get('label', ''),
                'description': metadata.get('description', ''),
                'category': metadata.get('category', 'custom'),
                'platform': 'flowise',
                'similarity_score': round(1.0 - distance, 3),  # Convert distance to similarity
                'inputs_count': metadata.get('inputs_count', 0),
                'code_lines': metadata.get('code_lines', 0),
                'has_code': metadata.get('has_code', False)
            }
            
            formatted_results.append(result)
            
        return formatted_results

    def get_component_by_name(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific Flowise component by name"""
        
        try:
            results = self.collection.get(
                ids=[component_name],
                include=['metadatas', 'documents']
            )
            
            if results['ids']:
                metadata = results['metadatas'][0] if results['metadatas'] else {}
                return {
                    'component_id': component_name,
                    'name': metadata.get('name', ''),
                    'label': metadata.get('label', ''),
                    'description': metadata.get('description', ''),
                    'category': metadata.get('category', 'custom'),
                    'platform': 'flowise',
                    'file_path': metadata.get('file_path', ''),
                    'code_lines': metadata.get('code_lines', 0)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get component",
                component_name=component_name,
                error=str(e)
            )
            
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get Flowise RAG engine statistics"""
        
        try:
            collection_count = self.collection.count()
            
            return {
                'total_components': collection_count,
                'collection_name': self.collection_name,
                'persist_directory': self.persist_directory,
                'components_directory': self.components_dir,
                'platform': 'flowise'
            }
            
        except Exception as e:
            self.logger.error("Failed to get stats", error=str(e))
            return {
                'total_components': 0,
                'collection_name': self.collection_name,
                'error': str(e),
                'platform': 'flowise'
            }