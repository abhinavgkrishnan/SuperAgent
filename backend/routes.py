import json
import logging
from flask import jsonify, request, Response, stream_with_context
from models import db, GeneratedContent
from agents.thesis_agent import ThesisAgent
from agents.twitter_agent import TwitterAgent
from agents.serper_agent import SerperAgent
from agents.data_analysis_agent import DataAnalysisAgent
from agents.financial_agent import FinancialReportAgent
from agents.product_description_agent import ProductDescriptionAgent
from agents.super_agent import SuperAgent

logger = logging.getLogger(__name__)

# Initialize agents
serper_agent = SerperAgent()
thesis_agent = ThesisAgent()
twitter_agent = TwitterAgent()
data_analysis_agent = DataAnalysisAgent()
financial_agent = FinancialReportAgent()
product_description_agent = ProductDescriptionAgent()

# Initialize SuperAgent with specialized agents
specialized_agents = {
    'thesis': thesis_agent,
    'twitter': twitter_agent,
    'data_analysis': data_analysis_agent,
    'financial': financial_agent,
    'product': product_description_agent
}
super_agent = SuperAgent(search_agent=serper_agent, specialized_agents=specialized_agents)

def init_routes(app):
    @app.route('/api/generate', methods=['POST'])
    def generate_content():
        if not request.is_json:
            logger.error("Request content-type is not application/json")
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        try:
            data = request.get_json()
            if not data or 'prompt' not in data:
                logger.error("No prompt provided in request data")
                return jsonify({'error': 'No prompt provided'}), 400

            prompt = data['prompt']
            logger.info(f"Received prompt: {prompt}")

            # Let SuperAgent determine content type and select appropriate agent
            content_type = super_agent.determine_content_type(prompt)
            agent = super_agent.get_agent_for_type(content_type)
            logger.info(f"Content type determined by SuperAgent: {content_type}")

            # Get search results based on content type
            search_type = "scholar" if content_type in ["thesis", "data_analysis"] else "general"
            search_results = serper_agent.search(prompt, search_type)
            logger.info(f"Retrieved {len(search_results)} search results")

            def generate():
                try:
                    accumulated_content = ""
                    for chunk in agent.generate(prompt, search_results=search_results):
                        try:
                            if isinstance(chunk, str):
                                chunk_data = json.loads(chunk)
                                if 'content' in chunk_data:
                                    accumulated_content += chunk_data['content']
                                    if content_type == 'data_analysis':
                                        logger.info(f"Processing data analysis chunk: {chunk_data}")
                                    yield f"data: {json.dumps(chunk_data)}\n\n"
                                else:
                                    logger.warning(f"Invalid chunk format: {type(chunk)}")
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error in chunk: {e}, chunk: {chunk}")
                            continue

                    yield "data: [DONE]\n\n"

                    # Log the complete content to database
                    content_entry = GeneratedContent(
                        prompt=prompt,
                        content=accumulated_content,
                        content_type=content_type,
                        meta_info={
                            'agent_type': content_type,
                            'search_type': search_type,
                            'search_results_count': len(search_results)
                        }
                    )
                    db.session.add(content_entry)
                    db.session.commit()
                    logger.info(f"Content logged to database with ID: {content_entry.id}")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error in content generation: {error_msg}")
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"

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