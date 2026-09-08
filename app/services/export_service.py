import os
import json
import hashlib
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models.export import ExportRecord
from app.models.search import SearchHistory
from app.models.article import Article
from app.models.fact_check import FactCheckResult
from app.models.sentiment import SentimentResult
from app.models.evolution import EvolutionResult
from app.models.report import ResearchReport, ComparisonResult

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Custom canvas to compute total page count and draw page numbers, headers, and footers"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Prevent page count from exceeding hard safety constraint of 500 pages
        if page_count > 500:
            page_count = 500

        self.saveState()
        
        # Suppress headers/footers on cover/first page
        if self._pageNumber > 1:
            # Draw header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#4f46e5"))
            self.drawString(54, 750, "MET RESEARCH PLATFORM — EVIDENCE DOSSIER")
            
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
            
            # Draw footer
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawString(54, 36, "CONFIDENTIAL — FOR RESEARCH PURPOSES ONLY")
            
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(558, 36, page_text)
            
        self.restoreState()


class ExportService:
    """Service to handle generation, caching, and recovery of investigation evidence dossier exports"""

    def __init__(self):
        # Root directory for exports
        self.exports_dir = os.path.join(current_app.instance_path, 'exports')
        os.makedirs(self.exports_dir, exist_ok=True)

    def get_or_create_export(self, user_id, export_type, source_type, source_id, export_format):
        """Retrieves an existing completed export (cache hit) or compiles a new one"""
        # Ensure user folder exists
        user_dir = os.path.join(self.exports_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)

        # 1. Query for existing record
        record = ExportRecord.query.filter_by(
            user_id=user_id,
            export_type=export_type,
            source_type=source_type,
            source_id=source_id,
            export_format=export_format,
            status='completed'
        ).first()

        if record:
            # Verify file exists on disk
            if os.path.exists(record.file_path):
                # Calculate and verify hash
                h = self._calculate_sha256(record.file_path)
                if h == record.file_hash:
                    current_app.logger.info(f"Export cache hit: {record.file_name}")
                    return record
                else:
                    current_app.logger.warning(f"Export file corrupted on disk: {record.file_name}. Rebuilding...")
            else:
                current_app.logger.info(f"Export file missing from disk: {record.file_name}. Rebuilding from snapshot_json...")
            
            # Auto-regenerate file from stored snapshot_json
            try:
                self._write_file_from_snapshot(record)
                return record
            except Exception as e:
                current_app.logger.error(f"Failed to rebuild file from snapshot: {str(e)}")
                # Continue below to generate fresh if rebuild fails

        # 2. No record or failed rebuild: generate fresh snapshot data
        snapshot_data = self._compile_snapshot_data(user_id, export_type, source_type, source_id)
        
        # Enforce max article size limits on dossier (100 articles)
        if export_type == 'dossier' and len(snapshot_data.get('articles', [])) > 100:
            raise ValueError("Maximum dossier size exceeded. Limit is 100 articles.")

        # Create new record in DB
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = export_format.lower()
        file_name = f"export_{export_type}_{source_id}_{timestamp}.{ext}"
        file_path = os.path.join(user_dir, file_name)

        record = ExportRecord(
            user_id=user_id,
            export_type=export_type,
            source_type=source_type,
            source_id=source_id,
            file_name=file_name,
            file_path=file_path,
            export_format=ext,
            status='pending',
            snapshot_json=json.dumps(snapshot_data)
        )
        db.session.add(record)
        db.session.flush()

        try:
            self._write_file_from_snapshot(record)
            record.status = 'completed'
            db.session.commit()

            # Automatically guarantee a copy in user's local Downloads folder
            try:
                import shutil
                dl_folders = [
                    os.path.expanduser(r'~\Downloads'),
                    r'C:\Users\laksh\Downloads',
                    r'C:\Users\laksh\workspace\Downloads'
                ]
                for dl_dir in dl_folders:
                    if os.path.exists(dl_dir) and os.path.exists(record.file_path):
                        shutil.copyfile(record.file_path, os.path.join(dl_dir, record.file_name))
            except Exception:
                pass

            return record
        except Exception as e:
            db.session.rollback()
            record.status = 'failed'
            db.session.commit()
            raise e

    def _calculate_sha256(self, filepath):
        """Computes the SHA256 checksum of a file on disk"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def _compile_snapshot_data(self, user_id, export_type, source_type, source_id):
        """Compiles a complete immutable data dictionary for the snapshot report"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "export_type": export_type,
            "source_type": source_type,
            "source_id": source_id,
            "user_id": user_id
        }

        if source_type == 'search':
            search = db.session.get(SearchHistory, source_id)
            if not search:
                raise ValueError(f"Search history query ID {source_id} not found.")
            data["search"] = search.to_dict()

            # Load articles
            articles = db.session.query(Article).filter_by(search_id=source_id).all()
            data["articles"] = []
            for art in articles:
                art_dict = {
                    "id": art.id,
                    "title": art.title,
                    "content": art.content[:5000] if art.content else "", # Max 5,000 chars per article constraint
                    "url": art.url,
                    "source": art.source or "Unknown",
                    "published_at": art.published_at.isoformat() if art.published_at else None
                }
                
                # Fetch credibility details
                from app.models.credibility import SourceCredibility
                cred = db.session.query(SourceCredibility).filter_by(domain=art.source).first()
                if cred:
                    art_dict["source_credibility_score"] = cred.credibility_score
                    art_dict["source_letter_grade"] = cred.letter_grade
                else:
                    art_dict["source_credibility_score"] = 70.0
                    art_dict["source_letter_grade"] = "C"
                
                # Fetch fact audit if fact_audit type or dossier
                if export_type in ('fact_audit', 'dossier'):
                    fa = db.session.query(FactCheckResult).filter_by(article_id=art.id).first()
                    art_dict["fact_check"] = fa.to_dict() if fa else None

                # Fetch sentiment if sentiment or dossier
                if export_type in ('sentiment', 'dossier'):
                    sent = db.session.query(SentimentResult).filter_by(article_id=art.id).first()
                    art_dict["sentiment"] = sent.to_dict() if sent else None

                data["articles"].append(art_dict)

            # Fetch evolution if evolution or dossier
            if export_type in ('evolution', 'dossier'):
                evo = db.session.query(EvolutionResult).filter_by(search_id=source_id).first()
                data["evolution"] = evo.to_dict() if evo else None

            # Fetch explainability snapshot
            from app.models.explainability import ExplainabilityResult
            xai = db.session.query(ExplainabilityResult).filter_by(search_id=source_id, explanation_type='search').first()
            if xai:
                data["explainability"] = xai.to_dict()
            else:
                try:
                    from app.services.explainability_service import ExplainabilityService
                    svc = ExplainabilityService()
                    data["explainability"] = svc.generate_search_explainability(source_id)
                except Exception:
                    data["explainability"] = None

        elif source_type == 'report':
            report = db.session.get(ResearchReport, source_id)
            if not report:
                raise ValueError(f"Research report ID {source_id} not found.")
            data["report"] = report.to_dict()

            comp = db.session.query(ComparisonResult).filter_by(report_id=source_id).first()
            data["comparison"] = comp.to_dict() if comp else None

            # Generate sub-profiles for compared searches
            data["search_profiles"] = []
            for sid in report.search_ids:
                search_obj = db.session.get(SearchHistory, sid)
                if search_obj:
                    data["search_profiles"].append(search_obj.to_dict())

            # Fetch explainability snapshot for report
            from app.models.explainability import ExplainabilityResult
            xai = db.session.query(ExplainabilityResult).filter_by(search_id=None, article_id=source_id, explanation_type='report').first()
            if xai:
                data["explainability"] = xai.to_dict()
            else:
                try:
                    from app.services.explainability_service import ExplainabilityService
                    svc = ExplainabilityService()
                    data["explainability"] = svc.generate_report_explainability(source_id)
                except Exception:
                    data["explainability"] = None

        return data

    def _write_file_from_snapshot(self, record):
        """Builds and writes the physical export file to disk using the stored snapshot JSON"""
        snapshot_data = json.loads(record.snapshot_json)
        fmt = record.export_format.lower()

        if fmt == 'json':
            content = json.dumps(snapshot_data, indent=2)
            # PDF Safety Constraints check: max total text 2MB
            if len(content.encode('utf-8')) > 2 * 1024 * 1024:
                raise ValueError("Export size limit exceeded. Max text size is 2MB.")
            with open(record.file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        elif fmt == 'html':
            content = self._render_snapshot_html(snapshot_data)
            if len(content.encode('utf-8')) > 2 * 1024 * 1024:
                raise ValueError("Export size limit exceeded. Max text size is 2MB.")
            with open(record.file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        elif fmt == 'pdf':
            # Builds PDF via ReportLab
            self._render_snapshot_pdf(snapshot_data, record.file_path)

        else:
            raise ValueError(f"Unsupported export format: {fmt}")

        # Update file size and hash
        record.file_size = os.path.getsize(record.file_path)
        record.file_hash = self._calculate_sha256(record.file_path)

    def _render_snapshot_html(self, data):
        """Generates a standalone beautiful HTML view of the snapshot"""
        # Render dynamic details depending on type
        title = f"MET Research Export — {data['export_type'].replace('_', ' ').upper()}"
        created_time = data["generated_at"]
        
        body_content = ""
        
        if "search" in data:
            search = data["search"]
            body_content += f"""
            <div class="card bg-white p-6 rounded-2xl border border-slate-100 mb-6">
                <h2 class="text-lg font-bold text-slate-800 mb-2">Search Query Details</h2>
                <table class="w-full text-sm">
                    <tr><td class="font-semibold text-slate-500 py-1" style="width: 30%;">Query:</td><td class="text-slate-800 font-medium py-1">{search['query']}</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Type:</td><td class="text-slate-800 py-1">{search['search_type'] or 'general'}</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Fact Verdict:</td><td class="text-slate-800 py-1"><span class="badge badge-emerald">{search['fact_check_result'] or 'UNAUDITED'}</span></td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Overall Emotion:</td><td class="text-slate-800 py-1">{search['overall_emotion'] or 'Neutral'} ({search['overall_risk_level'] or 'LOW'} Risk)</td></tr>
                </table>
                <div class="mt-4 p-4 bg-slate-50 rounded-xl">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Narrative Summary</h3>
                    <p class="text-xs text-slate-700 leading-relaxed font-medium">{search['summary'] or 'No summary compiled.'}</p>
                </div>
            </div>
            """
            
        if "articles" in data:
            body_content += f"""
            <div class="card bg-white p-6 rounded-2xl border border-slate-100 mb-6">
                <h2 class="text-lg font-bold text-slate-800 mb-4">Collected Evidence Sources ({len(data['articles'])})</h2>
                <div class="space-y-4">
            """
            for art in data["articles"]:
                fact_verdict = ""
                if "fact_check" in art and art["fact_check"]:
                    fc = art["fact_check"]
                    fact_verdict = f"<span class='text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-bold ml-2'>{fc['truth_rating']} ({fc['confidence_score']:.1f})</span>"
                
                emotion_tag = ""
                if "sentiment" in art and art["sentiment"]:
                    s = art["sentiment"]
                    emotion_tag = f"<span class='text-[10px] bg-rose-50 text-rose-600 px-2 py-0.5 rounded-full font-bold ml-2'>{s['dominant_emotion']} ({s['risk_level']} Risk)</span>"

                cred_badge = ""
                if "source_credibility_score" in art:
                    score = art["source_credibility_score"]
                    grade = art.get("source_letter_grade", "C")
                    if grade in ('A+', 'A'):
                        bg_color = 'bg-emerald-50 text-emerald-600'
                    elif grade in ('B', 'C'):
                        bg_color = 'bg-amber-50 text-amber-600'
                    else:
                        bg_color = 'bg-rose-50 text-rose-600'
                    cred_badge = f"<span class='text-[10px] {bg_color} px-2 py-0.5 rounded-full font-bold ml-2'>Trust: {grade} ({score:.0f}%)</span>"

                body_content += f"""
                <div class="border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
                    <h3 class="text-sm font-bold text-slate-800">{art['title']}{fact_verdict}{emotion_tag}{cred_badge}</h3>
                    <p class="text-[10px] text-slate-400 font-mono mt-1">Source: {art['source']} | Published: {art['published_at'] or 'Unknown'}</p>
                    <p class="text-xs text-slate-700 mt-2 line-clamp-3">{art['content'][:400]}...</p>
                </div>
                """
            body_content += "</div></div>"

        if "evolution" in data and data["evolution"]:
            evo = data["evolution"]
            body_content += f"""
            <div class="card bg-white p-6 rounded-2xl border border-slate-100 mb-6">
                <h2 class="text-lg font-bold text-slate-800 mb-2">Narrative Mutation & Evolution</h2>
                <table class="w-full text-sm mb-4">
                    <tr><td class="font-semibold text-slate-500 py-1" style="width: 30%;">Total Variants:</td><td class="text-slate-800 font-semibold py-1">{evo['total_variants_detected']}</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Narrative Drift Score:</td><td class="text-slate-850 font-bold py-1">{evo['narrative_drift_score']:.1f}%</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Dominant Theme:</td><td class="text-slate-800 py-1">{evo['dominant_narrative'] or 'Unknown'}</td></tr>
                </table>
                <div class="p-4 bg-slate-50 rounded-xl">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Evolution Summary</h3>
                    <p class="text-xs text-slate-700 leading-relaxed font-medium">{evo['evolution_summary'] or 'No summary compiled.'}</p>
                </div>
            </div>
            """

        if "report" in data:
            rep = data["report"]
            comp = data.get("comparison", {})
            body_content += f"""
            <div class="card bg-white p-6 rounded-2xl border border-slate-100 mb-6">
                <h2 class="text-lg font-bold text-slate-800 mb-2">Comparative Analytics Report</h2>
                <table class="w-full text-sm mb-4">
                    <tr><td class="font-semibold text-slate-500 py-1" style="width: 30%;">Report Title:</td><td class="text-slate-800 font-bold py-1">{rep['report_name']}</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Similarity Index:</td><td class="text-indigo-600 font-extrabold py-1">{comp.get('similarity_score', 0.0):.1f}/100</td></tr>
                </table>
                <div class="p-4 bg-slate-50 rounded-xl">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Research Summary</h3>
                    <p class="text-xs text-slate-700 leading-relaxed font-medium">{rep['summary'] or 'No summary compiled.'}</p>
                </div>
            </div>
            """
        if "explainability" in data and data["explainability"]:
            xai = data["explainability"]
            exp = xai.get("explanation", {})
            
            features_html = ""
            for fi in xai.get("feature_importance", []):
                bg_c = '#ecfdf5' if fi['direction']=='supports_prediction' else '#fef2f2'
                fg_c = '#065f46' if fi['direction']=='supports_prediction' else '#991b1b'
                features_html += f"""
                <span style="background-color: {bg_c}; color: {fg_c}; display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-right: 4px; margin-bottom: 4px; font-weight: bold;">
                    {fi['feature']}: {fi['importance']:.2f}
                </span>
                """
                
            evidence_html = ""
            for ev in xai.get("evidence_for", []):
                evidence_html += f"<li><b>{ev['source_domain']}</b>: {ev['evidence_snippet']} (Grade: {ev['credibility_grade']})</li>"
            for ev in xai.get("evidence_against", []):
                evidence_html += f"<li><b>{ev['source_domain']}</b> (Counter): {ev['evidence_snippet']} (Grade: {ev['credibility_grade']})</li>"
                
            body_content += f"""
            <div class="card bg-white p-6 rounded-2xl border border-slate-100 mb-6">
                <h2 class="text-lg font-bold text-slate-800 mb-2">AI Explainability & Model Governance</h2>
                <table class="w-full text-sm mb-4">
                    <tr><td class="font-semibold text-slate-500 py-1" style="width: 30%;">Confidence Level:</td><td class="text-indigo-600 font-extrabold py-1">{xai['confidence_level']} ({xai['confidence']:.1f}%)</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Model Name / Version:</td><td class="text-slate-800 py-1">{xai['model_name']} ({xai['model_version']})</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Vectorizer Version:</td><td class="text-slate-800 py-1">{xai['vectorizer_version']}</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Pipeline Version:</td><td class="text-slate-800 py-1">{xai['pipeline_version']}</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Inference Method:</td><td class="text-slate-800 py-1">{xai['inference_method'].upper()} (Fallback: {str(xai['fallback_used']).upper()})</td></tr>
                    <tr><td class="font-semibold text-slate-500 py-1">Processing Time:</td><td class="text-slate-800 py-1">{xai['processing_time_ms']} ms</td></tr>
                </table>
                
                <div style="margin-bottom: 12px; padding: 12px; background-color: #f8fafc; border-radius: 8px;">
                    <h3 style="font-size: 11px; font-weight: bold; color: #475569; margin: 0 0 6px 0; text-transform: uppercase;">Executive Summary</h3>
                    <p style="font-size: 12px; margin: 0; color: #334155; line-height: 1.4;">{exp.get('Executive Summary', 'N/A')}</p>
                </div>
                
                <div style="margin-bottom: 12px; padding: 12px; background-color: #f8fafc; border-radius: 8px;">
                    <h3 style="font-size: 11px; font-weight: bold; color: #475569; margin: 0 0 6px 0; text-transform: uppercase;">Evidence Corroboration</h3>
                    <ul style="font-size: 12px; margin: 0; padding-left: 16px; color: #334155; line-height: 1.4;">
                        {evidence_html or '<li>No detailed evidence segments cached.</li>'}
                    </ul>
                </div>

                <div style="margin-bottom: 12px; padding: 12px; background-color: #f8fafc; border-radius: 8px;">
                    <h3 style="font-size: 11px; font-weight: bold; color: #475569; margin: 0 0 6px 0; text-transform: uppercase;">Feature Importance Weights</h3>
                    <div style="margin-top: 5px;">
                        {features_html or '<span>No features importance scores calculated.</span>'}
                    </div>
                </div>

                <div style="padding: 12px; background-color: #f8fafc; border-radius: 8px;">
                    <h3 style="font-size: 11px; font-weight: bold; color: #475569; margin: 0 0 6px 0; text-transform: uppercase;">Confidence Explanation & Limitations</h3>
                    <p style="font-size: 12px; margin: 0 0 6px 0; color: #334155;"><b>Confidence Details:</b> {exp.get('Confidence Explanation', 'N/A')}</p>
                    <p style="font-size: 12px; margin: 0 0 6px 0; color: #334155;"><b>Model Limitations:</b> {exp.get('Model Limitations', 'N/A')}</p>
                    <p style="font-size: 12px; margin: 0; color: #334155;"><b>Overall Recommendation:</b> {exp.get('Overall Recommendation', 'N/A')}</p>
                </div>
            </div>
            """
        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f8fafc; color: #1e293b; line-height: 1.5; padding: 40px; max-width: 800px; margin: 0 auto; }}
                .card {{ background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
                h1 {{ font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 0; margin-bottom: 4px; }}
                h2 {{ font-size: 15px; font-weight: 700; color: #4f46e5; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0; }}
                .badge {{ display: inline-block; padding: 2px 8px; font-size: 11px; font-weight: 700; border-radius: 9999px; text-transform: uppercase; }}
                .badge-emerald {{ background-color: #ecfdf5; color: #059669; }}
                .line-clamp-3 {{ display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
                .footer {{ text-align: center; font-size: 11px; color: #94a3b8; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div style="border-bottom: 2px solid #4f46e5; padding-bottom: 12px; margin-bottom: 24px;">
                <h1>{title}</h1>
                <div style="font-size: 11px; font-weight: bold; color: #64748b; text-transform: uppercase;">
                    Generated: {created_time} • Confidential Document
                </div>
            </div>

            {body_content}

            <div class="footer">
                MET Research Platform • Investigation Evidence Archive Dossier
            </div>
        </body>
        </html>
        """
        return html

    def _render_snapshot_pdf(self, data, file_path):
        """Generates a professional multi-page PDF using ReportLab Flowables"""
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            leftMargin=54, rightMargin=54,
            topMargin=72, bottomMargin=72
        )

        styles = getSampleStyleSheet()
        
        # Modify existing styles to avoid conflicts
        styles['Normal'].textColor = colors.HexColor("#1e293b")
        styles['Normal'].fontSize = 9
        styles['Normal'].leading = 13
        
        # Add custom unique paragraph styles
        styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#1e1b4b"),
            spaceAfter=15
        ))
        
        styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4f46e5"),
            spaceAfter=30,
            textTransform='uppercase'
        ))

        styles.add(ParagraphStyle(
            name='SecHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#4f46e5"),
            spaceBefore=15,
            spaceAfter=8,
            keepWithNext=True
        ))

        styles.add(ParagraphStyle(
            name='SubSecHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        ))

        styles.add(ParagraphStyle(
            name='SummaryText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#334155"),
            backColor=colors.HexColor("#f1f5f9"),
            borderColor=colors.HexColor("#cbd5e1"),
            borderWidth=0.5,
            borderPadding=12,
            spaceAfter=15,
            borderRadius=6
        ))

        story = []

        # ------------------ COVER PAGE ------------------
        story.append(Spacer(1, 100))
        story.append(Paragraph("MET EVIDENCE DOSSIER", styles['CoverSubtitle']))
        
        export_title = f"Investigation Report: {data['export_type'].replace('_', ' ').title()}"
        story.append(Paragraph(export_title, styles['CoverTitle']))
        story.append(Spacer(1, 15))
        
        # Horizontal rule
        rule_table = Table([[""]], colWidths=[504], rowHeights=[2])
        rule_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#4f46e5")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(rule_table)
        story.append(Spacer(1, 30))

        # Metadata table
        meta_data = [
            [Paragraph("<b>Generated Timestamp:</b>", styles['Normal']), Paragraph(data['generated_at'], styles['Normal'])],
            [Paragraph("<b>Export Source ID:</b>", styles['Normal']), Paragraph(str(data['source_id']), styles['Normal'])],
            [Paragraph("<b>Export Type:</b>", styles['Normal']), Paragraph(data['export_type'].upper(), styles['Normal'])],
            [Paragraph("<b>System Attribution:</b>", styles['Normal']), Paragraph("MET Automated Intelligence Engine v1.0", styles['Normal'])],
        ]
        meta_table = Table(meta_data, colWidths=[150, 354])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ]))
        story.append(meta_table)
        story.append(PageBreak())

        # ------------------ CONTENT ------------------
        # Total text size tracker
        total_text_chars = 0

        # Section 1: Executive Summary
        story.append(Paragraph("1. Executive Summary", styles['SecHeading']))
        summary_text = ""
        if "search" in data:
            summary_text = data["search"].get("summary") or "No narrative summary compiled."
        elif "report" in data:
            summary_text = data["report"].get("summary") or "No comparative summary compiled."
        
        # Enforce characters limit on executive summary
        summary_text = summary_text[:5000]
        total_text_chars += len(summary_text)
        story.append(Paragraph(summary_text, styles['SummaryText']))
        story.append(Spacer(1, 15))

        # Section 2: Search Information / Comparative Metadata
        if "search" in data:
            search = data["search"]
            story.append(Paragraph("2. Search Query Metadata", styles['SecHeading']))
            query_details = [
                [Paragraph("<b>Query:</b>", styles['Normal']), Paragraph(search.get('query') or '', styles['Normal'])],
                [Paragraph("<b>Search Type:</b>", styles['Normal']), Paragraph(search.get('search_type') or 'general', styles['Normal'])],
                [Paragraph("<b>Fact Verdict:</b>", styles['Normal']), Paragraph(search.get('fact_check_result') or 'UNAUDITED', styles['Normal'])],
                [Paragraph("<b>Overall Emotion:</b>", styles['Normal']), Paragraph(search.get('overall_emotion') or 'Neutral', styles['Normal'])],
                [Paragraph("<b>Overall Risk Level:</b>", styles['Normal']), Paragraph(search.get('overall_risk_level') or 'LOW', styles['Normal'])],
            ]
            qd_table = Table(query_details, colWidths=[150, 354])
            qd_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
            ]))
            story.append(qd_table)
            story.append(Spacer(1, 20))

        # Section 3 & 4: Fact Audit Results & Sentiment Intelligence (per article breakdown)
        if "articles" in data:
            story.append(Paragraph("3. Article Details & Veracity Audits", styles['SecHeading']))
            for idx, art in enumerate(data["articles"]):
                # Truncate content per article safety constraint (5000 chars)
                art_content = art.get("content") or ""
                art_content = art_content[:5000]
                total_text_chars += len(art_content)

                art_elements = []
                art_elements.append(Paragraph(f"Article {idx+1}: {art['title']}", styles['SubSecHeading']))
                
                cred_score = art.get("source_credibility_score", 70.0)
                cred_grade = art.get("source_letter_grade", "C")
                meta_str = f"<b>Source:</b> {art['source']} (Trust: {cred_grade}, {cred_score:.1f}%) | <b>Published:</b> {art['published_at'] or 'Unknown'}"
                art_elements.append(Paragraph(meta_str, styles['Normal']))
                
                # Check for fact audit
                if "fact_check" in art and art["fact_check"]:
                    fc = art["fact_check"]
                    fc_str = f"<b>Fact Verdict:</b> {fc['truth_rating']} (Confidence: {fc['confidence_score']:.1f}) | <b>Claim Evaluated:</b> {fc['claim']}"
                    art_elements.append(Paragraph(fc_str, styles['Normal']))

                # Check for sentiment analysis
                if "sentiment" in art and art["sentiment"]:
                    s = art["sentiment"]
                    sent_str = f"<b>Dominant Emotion:</b> {s['dominant_emotion']} (Risk: {s['risk_level']}) | <b>Confidence:</b> {s['confidence']:.1f}%"
                    art_elements.append(Paragraph(sent_str, styles['Normal']))

                # Sample content snippet (first 350 chars)
                content_snippet = art_content[:350] + "..." if len(art_content) > 350 else art_content
                art_elements.append(Spacer(1, 4))
                art_elements.append(Paragraph(f"<i>Content Snippet:</i> {content_snippet}", styles['Normal']))
                art_elements.append(Spacer(1, 12))

                story.append(KeepTogether(art_elements))

        # Section 5: Narrative Evolution Analysis
        if "evolution" in data and data["evolution"]:
            evo = data["evolution"]
            story.append(Paragraph("4. Narrative Evolution Metrics", styles['SecHeading']))
            evo_data = [
                [Paragraph("<b>Total Narrative Streams (Clusters):</b>", styles['Normal']), Paragraph(str(evo['total_variants_detected']), styles['Normal'])],
                [Paragraph("<b>Narrative Drift Score:</b>", styles['Normal']), Paragraph(f"{evo['narrative_drift_score']:.1f}%", styles['Normal'])],
                [Paragraph("<b>Dominant Theme:</b>", styles['Normal']), Paragraph(evo['dominant_narrative'] or 'Unknown', styles['Normal'])],
            ]
            evo_table = Table(evo_data, colWidths=[200, 304])
            evo_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
            ]))
            story.append(evo_table)
            story.append(Spacer(1, 15))

            # Timeline
            if evo.get("timeline"):
                story.append(Paragraph("Timeline Events Flow", styles['SubSecHeading']))
                for t in evo["timeline"]:
                    t_str = f"<b>Date:</b> {t.get('published_at') or 'Unknown'} | <b>Article:</b> {t['title']} (Drift: {t.get('drift_score', 0.0):.1f}%)"
                    story.append(Paragraph(t_str, styles['Normal']))
                    story.append(Spacer(1, 4))

        # Section 6: Comparative Intelligence (Report Source)
        if "report" in data:
            rep = data["report"]
            comp = data.get("comparison", {})
            story.append(Paragraph("5. Cross-Search Comparative Analytics", styles['SecHeading']))
            story.append(Paragraph(f"<b>Report Name:</b> {rep['report_name']}", styles['SubSecHeading']))
            
            comp_data = [
                [Paragraph("<b>Similarity Score:</b>", styles['Normal']), Paragraph(f"{comp.get('similarity_score', 0.0):.1f}/100", styles['Normal'])],
                [Paragraph("<b>Shared Themes:</b>", styles['Normal']), Paragraph(", ".join(comp.get('shared_themes', [])), styles['Normal'])],
            ]
            comp_table = Table(comp_data, colWidths=[150, 354])
            comp_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 15))

            # Shared claim pairs
            if comp.get("shared_claims"):
                story.append(Paragraph("Shared Claim Matches", styles['SubSecHeading']))
                for claim in comp["shared_claims"]:
                    claim_str = f"• '{claim['title_a']}' ↔ '{claim['title_b']}' (Match: {claim['similarity_score']*100:.1f}%)"
                    story.append(Paragraph(claim_str, styles['Normal']))
                    story.append(Spacer(1, 4))

        # Section 6.5: Explainability & Model Governance
        if "explainability" in data and data["explainability"]:
            xai = data["explainability"]
            exp = xai.get("explanation", {})
            story.append(Spacer(1, 15))
            story.append(Paragraph("5. AI Explainability & Model Governance", styles['SecHeading']))
            
            xai_meta = [
                [Paragraph("<b>Prediction:</b>", styles['Normal']), Paragraph(str(xai.get('prediction', 'N/A')), styles['Normal'])],
                [Paragraph("<b>Confidence Level:</b>", styles['Normal']), Paragraph(f"{xai.get('confidence_level', 'N/A')} ({xai.get('confidence', 0.0):.1f}%)", styles['Normal'])],
                [Paragraph("<b>Model Reference:</b>", styles['Normal']), Paragraph(f"{xai.get('model_name')} ({xai.get('model_version')})", styles['Normal'])],
                [Paragraph("<b>Pipeline Versions:</b>", styles['Normal']), Paragraph(f"Vectorizer: {xai.get('vectorizer_version')} | Pipeline: {xai.get('pipeline_version')}", styles['Normal'])],
                [Paragraph("<b>Inference Pipeline:</b>", styles['Normal']), Paragraph(f"Method: {xai.get('inference_method')} (Fallback Used: {str(xai.get('fallback_used')).upper()})", styles['Normal'])],
                [Paragraph("<b>Processing Latency:</b>", styles['Normal']), Paragraph(f"{xai.get('processing_time_ms')} ms", styles['Normal'])],
            ]
            xai_meta_table = Table(xai_meta, colWidths=[150, 354])
            xai_meta_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
            ]))
            story.append(xai_meta_table)
            story.append(Spacer(1, 12))

            story.append(Paragraph("<b>Executive Summary:</b>", styles['Normal']))
            story.append(Paragraph(exp.get('Executive Summary', 'N/A'), styles['SummaryText']))
            story.append(Spacer(1, 10))

            # Evidence lists formatting
            evidence_text = ""
            for ev in xai.get("evidence_for", []):
                evidence_text += f"• <b>{ev['source_domain']}</b>: {ev['evidence_snippet']} (Grade: {ev['credibility_grade']})<br/>"
            for ev in xai.get("evidence_against", []):
                evidence_text += f"• <b>{ev['source_domain']}</b> (Counter): {ev['evidence_snippet']} (Grade: {ev['credibility_grade']})<br/>"
                
            story.append(Paragraph("<b>Evidence Corroboration:</b>", styles['Normal']))
            story.append(Paragraph(evidence_text or "No detailed evidence segments loaded.", styles['Normal']))
            story.append(Spacer(1, 10))

            # Feature Importance table
            story.append(Paragraph("<b>Feature Importance Weights:</b>", styles['SubSecHeading']))
            fi_data = [["Feature", "Score", "Direction", "Description"]]
            for fi in xai.get("feature_importance", []):
                fi_data.append([
                    Paragraph(fi["feature"], styles['Normal']),
                    Paragraph(f"{fi['importance']:.2f}", styles['Normal']),
                    Paragraph(fi["direction"], styles['Normal']),
                    Paragraph(fi["description"], styles['Normal'])
                ])
            fi_table = Table(fi_data, colWidths=[120, 50, 110, 224])
            fi_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(fi_table)
            story.append(Spacer(1, 12))

            story.append(Paragraph("<b>Model Confidence & Limitations:</b>", styles['SubSecHeading']))
            story.append(Paragraph(f"<b>Confidence explanation:</b> {exp.get('Confidence Explanation', 'N/A')}", styles['Normal']))
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>Model limitations:</b> {exp.get('Model Limitations', 'N/A')}", styles['Normal']))
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>Overall Recommendation:</b> {exp.get('Overall Recommendation', 'N/A')}", styles['Normal']))

        # Section 7: Supporting Evidence Sources
        if "articles" in data and data["articles"]:
            story.append(Spacer(1, 15))
            story.append(Paragraph("6. References & Evidence URL Archives (Credibility Audit)", styles['SecHeading']))
            ref_data = [["Title", "Source Domain", "Trust", "Score", "URL"]]
            for art in data["articles"]:
                ref_data.append([
                    Paragraph(art['title'][:32]+"...", styles['Normal']),
                    Paragraph(art['source'], styles['Normal']),
                    Paragraph(art.get('source_letter_grade', 'C'), styles['Normal']),
                    Paragraph(f"{art.get('source_credibility_score', 70.0):.1f}%", styles['Normal']),
                    Paragraph(art['url'][:30]+"...", styles['Normal'])
                ])
            ref_table = Table(ref_data, colWidths=[120, 80, 50, 50, 204])
            ref_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(ref_table)

        # PDF Safety check on total characters compiled
        if total_text_chars > 2 * 1024 * 1024:
            raise ValueError("Export size limit exceeded. Max total text size is 2MB.")

        # Build PDF using custom dynamic NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
