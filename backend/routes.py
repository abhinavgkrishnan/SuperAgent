import json
import logging
from flask import jsonify, request, Response, stream_with_context
from models import db, GeneratedContent
from agents.thesis_agent import ThesisAgent
from agents.twitter_agent import TwitterAgent
from agents.serper_agent import SerperAgent
from agents.financial_agent import FinancialReportAgent
from agents.product_description_agent import ProductDescriptionAgent
from agents.super_agent import SuperAgent
from agents.fallback_agent import FallbackAgent

logger = logging.getLogger(__name__)

# Initialize agents
serper_agent = SerperAgent()
thesis_agent = ThesisAgent()
twitter_agent = TwitterAgent()
financial_agent = FinancialReportAgent()
product_description_agent = ProductDescriptionAgent()
fallback_agent = FallbackAgent()

# Initialize SuperAgent with specialized agents
specialized_agents = {
    'thesis': thesis_agent,
    'twitter': twitter_agent,
    'financial': financial_agent,
    'product': product_description_agent,
    'fallback': fallback_agent
}
super_agent = SuperAgent(search_agent=serper_agent, specialized_agents=specialized_agents)

def init_routes(app):
    @app.route('/api/generate', methods=['POST'])
    def generate_content():
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
    
        try:
            data = request.get_json()
            if not data or 'prompt' not in data:
                return jsonify({'error': 'No prompt provided'}), 400
    
            prompt = data['prompt']
            logger.info(f"Received prompt: {prompt}")
    
            def generate():
                try:
                    accumulated_content = ""
                    execution_info = {}
                    
                    for chunk in super_agent.generate(prompt):
                        try:
                            if isinstance(chunk, str):
                                chunk_data = json.loads(chunk)
                                if 'content' in chunk_data:
                                    accumulated_content += chunk_data['content']
                                    yield f"data: {json.dumps(chunk_data)}\n\n"
                                if 'execution_info' in chunk_data:
                                    execution_info = chunk_data['execution_info']
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error in chunk: {e}")
                            continue
    
                    yield "data: [DONE]\n\n"
    
                    # Log to database
                    content_entry = GeneratedContent(
                        prompt=prompt,
                        content=accumulated_content,
                        content_type=execution_info.get('content_type', 'unknown'),
                        meta_info={
                            'tools_used': super_agent.get_tools_used(),
                            'execution_path': super_agent.get_execution_path()
                        }
                    )
                    db.session.add(content_entry)
                    db.session.commit()
    
                except Exception as e:
                    logger.error(f"Error in generation: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive'
                }
            )
    
        except Exception as e:
            logger.error(f"Error in generate_content endpoint: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/history', methods=['GET'])
    def get_generation_history():
        """Endpoint to retrieve generation history"""
        try:
            entries = GeneratedContent.query.order_by(
                GeneratedContent.created_at.desc()
            ).limit(100).all()
            return jsonify([entry.to_dict() for entry in entries])
        except Exception as e:
            logger.error(f"Error retrieving history: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.query(GeneratedContent).first()
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'message': 'Service is running'
            }), 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500

    return app
