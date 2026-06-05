class VisualizationService:
    """Service to construct visualization config JSONs or charts for the dashboard UI"""
    
    def generate_sentiment_trends(self, article_ids):
        """Prepares coordinate plots for sentiment evolution (placeholder)"""
        return {
            "chart_type": "line",
            "labels": ["Day 1", "Day 2", "Day 3"],
            "datasets": [
                {
                    "label": "Sentiment Score",
                    "data": [0.1, -0.2, 0.4]
                }
            ]
        }

    def generate_evolution_graph(self, lineage_id):
        """Prepares node/link graphs for story lineages (placeholder)"""
        return {
            "chart_type": "network_graph",
            "nodes": [
                {"id": 1, "label": "Original Article"},
                {"id": 2, "label": "Mutation A"}
            ],
            "edges": [
                {"source": 1, "target": 2, "label": "rephrased"}
            ]
        }
