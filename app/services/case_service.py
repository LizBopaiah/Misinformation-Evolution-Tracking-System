from app.extensions import db
from app.models.case import InvestigationCase, CaseItem, CaseActivity
from app.models.search import SearchHistory
from app.models.sentiment import SentimentResult
from app.models.evolution import EvolutionResult
from app.models.report import ResearchReport
from app.models.export import ExportRecord
from datetime import datetime

class CaseService:
    """Service class for managing investigation cases and their associated items"""

    def create_case(self, user_id, title, description, status='OPEN', priority='MEDIUM'):
        """Creates a new investigation case and logs the activity"""
        case = InvestigationCase(
            user_id=user_id,
            title=title,
            description=description,
            status=status,
            priority=priority
        )
        db.session.add(case)
        db.session.flush()

        # Log activity
        activity = CaseActivity(
            case_id=case.id,
            action='CREATED_CASE'
        )
        db.session.add(activity)
        db.session.commit()
        return case

    def update_case(self, case_id, user_id, **kwargs):
        """Updates case details. Blocks write attempts if case is archived."""
        case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
        if not case:
            raise PermissionError("Case not found or access denied.")

        if case.status == 'ARCHIVED':
            raise ValueError("Cannot modify an archived case.")

        # Update attributes
        for key, val in kwargs.items():
            if hasattr(case, key):
                setattr(case, key, val)

        # Log activity
        action = 'UPDATED_CASE'
        if kwargs.get('status') == 'ARCHIVED':
            action = 'ARCHIVED_CASE'

        activity = CaseActivity(
            case_id=case.id,
            action=action
        )
        db.session.add(activity)
        db.session.commit()
        return case

    def archive_case(self, case_id, user_id):
        """Archives a case (soft-delete style)"""
        return self.update_case(case_id, user_id, status='ARCHIVED')

    def add_item(self, case_id, user_id, item_type, item_id):
        """Links an artifact to a case, verifying ownership and recording metadata snapshot"""
        case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
        if not case:
            raise PermissionError("Case not found or access denied.")

        if case.status == 'ARCHIVED':
            raise ValueError("Cannot modify an archived case.")

        # Check for duplicate item in case
        existing = db.session.query(CaseItem).filter_by(
            case_id=case_id,
            item_type=item_type,
            item_id=item_id
        ).first()
        if existing:
            raise ValueError("Artifact already linked to this case.")

        # Validate artifact ownership & extract metadata snapshot
        item_title = "Unknown Artifact"
        item_status = "completed"
        item_created_at = datetime.utcnow()

        if item_type == 'search':
            search = db.session.query(SearchHistory).filter_by(id=item_id).first()
            if not search:
                raise FileNotFoundError("Search history record not found.")
            if search.user_id != user_id:
                raise PermissionError("Access denied to this search record.")
            item_title = search.query
            item_status = search.search_status or 'completed'
            item_created_at = search.created_at

        elif item_type == 'sentiment':
            # Check if it points to a SentimentResult or a SearchHistory with sentiment
            sent_res = db.session.query(SentimentResult).filter_by(id=item_id).first()
            if sent_res:
                # Resolve SearchHistory owner
                search = db.session.query(SearchHistory).filter_by(id=sent_res.search_id).first()
                if not search or search.user_id != user_id:
                    raise PermissionError("Access denied to this sentiment record.")
                item_title = f"Sentiment - {sent_res.dominant_emotion or 'Neutral'}"
                item_status = sent_res.risk_level or 'LOW'
                item_created_at = sent_res.created_at
            else:
                # Fallback to checking if it is a SearchHistory ID with sentiment analyzed
                search = db.session.query(SearchHistory).filter_by(id=item_id).first()
                if not search:
                    raise FileNotFoundError("Sentiment record/search not found.")
                if search.user_id != user_id:
                    raise PermissionError("Access denied to this sentiment record.")
                item_title = f"Sentiment Analysis: {search.query}"
                item_status = "completed"
                item_created_at = search.sentiment_analyzed_at or search.created_at

        elif item_type == 'evolution':
            evo = db.session.query(EvolutionResult).filter_by(id=item_id).first()
            if evo:
                if evo.user_id != user_id:
                    raise PermissionError("Access denied to this evolution record.")
                item_title = f"Evolution: {evo.dominant_narrative or 'General'}"
                item_status = f"{evo.narrative_drift_score or 0.0:.1f}% drift"
                item_created_at = evo.created_at
            else:
                # Check if search exists as fallback
                search = db.session.query(SearchHistory).filter_by(id=item_id).first()
                if not search:
                    raise FileNotFoundError("Evolution record/search not found.")
                if search.user_id != user_id:
                    raise PermissionError("Access denied to this evolution record.")
                item_title = f"Evolution Analysis: {search.query}"
                item_status = "completed"
                item_created_at = search.created_at

        elif item_type == 'comparison':
            report = db.session.query(ResearchReport).filter_by(id=item_id).first()
            if not report:
                raise FileNotFoundError("Research report not found.")
            if report.user_id != user_id:
                raise PermissionError("Access denied to this research report.")
            item_title = report.report_name
            item_status = 'completed'
            item_created_at = report.created_at

        elif item_type == 'export':
            export = db.session.query(ExportRecord).filter_by(id=item_id).first()
            if not export:
                raise FileNotFoundError("Export record not found.")
            if export.user_id != user_id:
                raise PermissionError("Access denied to this export record.")
            item_title = export.file_name
            item_status = export.status or 'completed'
            item_created_at = export.created_at

        else:
            raise ValueError(f"Unsupported item type: {item_type}")

        # Create CaseItem
        case_item = CaseItem(
            case_id=case_id,
            item_type=item_type,
            item_id=item_id,
            item_title=item_title,
            item_status=item_status,
            item_created_at=item_created_at
        )
        db.session.add(case_item)

        # Log activity
        activity = CaseActivity(
            case_id=case_id,
            action='ATTACHED_ITEM',
            item_type=item_type,
            item_id=item_id
        )
        db.session.add(activity)
        db.session.commit()
        return case_item

    def remove_item(self, case_id, user_id, item_type, item_id):
        """Detaches an artifact from a case, logging the activity"""
        case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
        if not case:
            raise PermissionError("Case not found or access denied.")

        if case.status == 'ARCHIVED':
            raise ValueError("Cannot modify an archived case.")

        item = db.session.query(CaseItem).filter_by(
            case_id=case_id,
            item_type=item_type,
            item_id=item_id
        ).first()
        if not item:
            raise FileNotFoundError("Linked case item not found.")

        db.session.delete(item)

        # Log activity
        activity = CaseActivity(
            case_id=case_id,
            action='DETACHED_ITEM',
            item_type=item_type,
            item_id=item_id
        )
        db.session.add(activity)
        db.session.commit()
        return True

    def get_case_dashboard(self, case_id, user_id, page=1, page_size=25):
        """Returns paginated case artifacts using stored snapshot metadata"""
        case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
        if not case:
            raise PermissionError("Case not found or access denied.")

        # Query items paginated
        query = db.session.query(CaseItem).filter_by(case_id=case_id).order_by(CaseItem.created_at.desc())
        total_items = query.count()

        # Enforce page size caps
        if page_size < 1:
            page_size = 25
        elif page_size > 100:
            page_size = 100

        items_paginated = query.limit(page_size).offset((page - 1) * page_size).all()

        dashboard = {
            "case_details": case.to_dict(),
            "searches": [],
            "comparisons": [],
            "exports": [],
            "sentiments": [],
            "evolution": [],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": (total_items + page_size - 1) // page_size if total_items > 0 else 1
            }
        }

        # Distribute items based on item_type using metadata snapshots
        for item in items_paginated:
            item_dict = item.to_dict()
            if item.item_type == 'search':
                dashboard["searches"].append(item_dict)
            elif item.item_type == 'comparison':
                dashboard["comparisons"].append(item_dict)
            elif item.item_type == 'export':
                dashboard["exports"].append(item_dict)
            elif item.item_type == 'sentiment':
                dashboard["sentiments"].append(item_dict)
            elif item.item_type == 'evolution':
                dashboard["evolution"].append(item_dict)

        return dashboard

    def calculate_case_statistics(self, case_id, user_id):
        """Calculates granular counts and misinformation audits for linked case items"""
        case = db.session.query(InvestigationCase).filter_by(id=case_id, user_id=user_id).first()
        if not case:
            raise PermissionError("Case not found or access denied.")

        # Counts
        items = db.session.query(CaseItem).filter_by(case_id=case_id).all()
        
        search_ids = [item.item_id for item in items if item.item_type == 'search']
        sentiment_search_ids = [item.item_id for item in items if item.item_type == 'sentiment']
        evolution_search_ids = [item.item_id for item in items if item.item_type == 'evolution']
        
        # Misinformation Count: query SearchHistory for linked searches
        misinfo_count = 0
        if search_ids:
            misinfo_count = db.session.query(SearchHistory).filter(
                SearchHistory.id.in_(search_ids),
                SearchHistory.fact_check_result == 'MISINFORMATION DETECTED'
            ).count()

        # High Risk Sentiment Count: query SentimentResult for linked searches or linked sentiments
        all_sentiment_source_ids = list(set(search_ids + sentiment_search_ids + evolution_search_ids))
        high_risk_sentiment_count = 0
        if all_sentiment_source_ids:
            high_risk_sentiment_count = db.session.query(SentimentResult).filter(
                SentimentResult.search_id.in_(all_sentiment_source_ids),
                SentimentResult.risk_level == 'HIGH'
            ).count()

        # Last activity
        last_act = db.session.query(CaseActivity).filter_by(case_id=case_id).order_by(CaseActivity.created_at.desc()).first()
        last_activity_time = last_act.created_at.isoformat() if last_act else None

        return {
            "search_count": sum(1 for item in items if item.item_type == 'search'),
            "comparison_count": sum(1 for item in items if item.item_type == 'comparison'),
            "export_count": sum(1 for item in items if item.item_type == 'export'),
            "sentiment_count": sum(1 for item in items if item.item_type == 'sentiment'),
            "evolution_count": sum(1 for item in items if item.item_type == 'evolution'),
            "misinformation_count": misinfo_count,
            "high_risk_sentiment_count": high_risk_sentiment_count,
            "last_activity": last_activity_time
        }
