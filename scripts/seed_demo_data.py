import sys, os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models.user import User
from app.models.search import SearchHistory
from app.models.article import Article
from app.services.sentiment_service import SentimentService
from app.services.evolution_service import EvolutionService
from app.services.explainability_service import ExplainabilityService

app = create_app()
with app.app_context():
    print("Seeding demo user and search history...")
    
    # Ensure indexes
    db.session.execute(db.text("DROP INDEX IF EXISTS ix_articles_url"))
    db.session.execute(db.text("CREATE INDEX IF NOT EXISTS ix_articles_url ON articles (url)"))
    try:
        db.session.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_search_article_url ON articles (search_id, url)"))
    except Exception as e:
        print("Index notice:", e)

    # 1. Create or get user
    user = User.query.filter_by(email="researcher_test@example.com").first()
    if not user:
        user = User(
            username="liz_researcher",
            email="researcher_test@example.com",
            full_name="Liz"
        )
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        print("Created user:", user.email)
    else:
        user.full_name = "Liz"
        user.set_password("Password123!")
        db.session.commit()
        print("Existing user updated:", user.email)

    # 2. Seed 'COVID vaccine infertility'
    s1 = db.session.query(SearchHistory).filter_by(user_id=user.id, query="COVID vaccine infertility").first()
    if not s1:
        s1 = SearchHistory(
            user_id=user.id,
            query="COVID vaccine infertility",
            status="completed",
            search_status="completed",
            summary="Studies show that reproductive concerns remain one of the primary drivers of vaccine hesitancy among young adults. There is currently no evidence that any vaccines, including COVID-19 vaccines, cause fertility problems in women or men. Clinical data collected from tens of thousands of vaccinated individuals who became pregnant show no higher rates of pregnancy complications or fertility issues compared to the general population.",
            fact_check_result="MISINFORMATION DETECTED",
            articles_collected=6,
            processing_time=2.33
        )
        db.session.add(s1)
        db.session.commit()

    # Add 6 articles for s1
    articles_data = [
        ("FACT CHECK: Does the COVID-19 vaccine cause infertility in men or women?", "politifact.com", "https://www.politifact.com/factchecks/2021/dec/covid-vaccine-fertility-myth/", "Claims linking the COVID-19 vaccines to infertility are medically unfounded. Clinical trials and real-world studies show no association between the vaccines and reduced fertility in men or women."),
        ("How Misinformation Linking COVID-19 Vaccines to Infertility Spread on Social Media", "poynter.org", "https://www.poynter.org/fact-checking/2021/how-infertility-myth-spread/", "A breakdown of how false claims about fertility and COVID-19 vaccines proliferated across digital platforms, driven by misinterpretations of protein syncytin-1."),
        ("COVID-19 Vaccines and Fertility: What Clinical Data Really Shows", "cdc.gov", "https://www.cdc.gov/coronavirus/2019-ncov/vaccines/planning-for-pregnancy.html", "The CDC and major obstetric organizations confirm COVID-19 vaccination is recommended for people trying to get pregnant now or who might become pregnant in the future."),
        ("Reuters Fact Check: Unraveling Claims of Male Infertility", "reuters.com", "https://www.reuters.com/article/factcheck-coronavirus-vaccine-fertility-idUSL1N2MG123", "No evidence has been documented showing sperm parameters decline following mRNA vaccination, contrary to widely shared viral videos."),
        ("National Institutes of Health Study Confirms COVID Vaccines Do Not Affect Female Fertility", "nih.gov", "https://www.nih.gov/news-events/news-releases/covid-19-vaccination-does-not-reduce-chances-conception", "An extensive prospective study of couples trying to conceive found no difference in pregnancy chances between vaccinated and unvaccinated female partners."),
        ("Study: COVID-19 Vaccination Does Not Affect Male Semen Parameters", "jamanetwork.com", "https://jamanetwork.com/journals/jama/fullarticle/2781360", "In a study of healthy reproductive-age men evaluated before and after receiving mRNA vaccines, researchers found no significant decrease in any sperm parameter.")
    ]

    for title, source, url, content in articles_data:
        art = Article.query.filter_by(search_id=s1.id, url=url).first()
        if not art:
            art = Article(
                search_id=s1.id,
                user_id=user.id,
                title=title,
                source=source,
                url=url,
                content=content,
                content_hash="hash_" + str(abs(hash(url)))[:12]
            )
            db.session.add(art)
    db.session.commit()

    # Run sentiment on s1
    arts = Article.query.filter_by(search_id=s1.id).all()
    sent_svc = SentimentService()
    try:
        sent_svc._load_model()
        texts = [a.content for a in arts]
        outputs = sent_svc.analyze_texts_batch(texts)
        from app.models.sentiment import SentimentResult
        distributions = []
        for a, out in zip(arts, outputs):
            sr = SentimentResult.query.filter_by(article_id=a.id, search_id=s1.id).first()
            if not sr:
                sr = SentimentResult(article_id=a.id, search_id=s1.id)
                db.session.add(sr)
            sr.dominant_emotion = out["dominant_emotion"]
            sr.confidence = out["confidence"]
            sr.emotion_distribution = out["distribution"]
            sr.risk_level = out["risk_level"]
            sr.model_version = out["model_version"]
            distributions.append(out["distribution"])
        agg = sent_svc.aggregate_results(distributions)
        s1.overall_emotion = agg["overall_emotion"]
        s1.overall_risk_level = agg["overall_risk_level"]
        s1.aggregated_emotion_distribution = agg["emotion_distribution"]
        from datetime import datetime, timezone
        s1.sentiment_analyzed_at = datetime.now(timezone.utc)
        db.session.commit()
        print("Computed sentiment for s1:", s1.overall_emotion)
    except Exception as e:
        print("Sentiment generation notice:", e)

    # Run evolution on s1
    evo_svc = EvolutionService()
    try:
        res = evo_svc.analyze_evolution(arts)
        from app.models.evolution import EvolutionResult
        er = EvolutionResult.query.filter_by(search_id=s1.id).first()
        if not er:
            er = EvolutionResult(
                search_id=s1.id,
                user_id=user.id,
                baseline_article_id=res["baseline_article_id"],
                narrative_drift_score=res["narrative_drift_score"],
                total_variants_detected=res["total_variants_detected"],
                dominant_narrative=res["dominant_narrative"],
                evolution_summary=res["evolution_summary"]
            )
            er.mutation_points = res["mutation_points"]
            er.timeline = res["timeline"]
            db.session.add(er)
            db.session.commit()
        print("Computed evolution for s1:", res["narrative_drift_score"])
    except Exception as e:
        print("Evolution generation notice:", e)

    # 3. Seed '5G causes cancer'
    s2 = db.session.query(SearchHistory).filter_by(user_id=user.id, query="5G causes cancer").first()
    if not s2:
        s2 = SearchHistory(
            user_id=user.id,
            query="5G causes cancer",
            status="completed",
            search_status="completed",
            summary="Scientific organizations including the WHO and FCC confirm that 5G radiofrequency radiation operates at non-ionizing levels and causes no cellular damage or cancer.",
            fact_check_result="MISINFORMATION DETECTED",
            articles_collected=1,
            processing_time=1.74
        )
        db.session.add(s2)
        db.session.commit()

    art5g = Article.query.filter_by(search_id=s2.id).first()
    if not art5g:
        art5g = Article(
            search_id=s2.id,
            user_id=user.id,
            title="Snopes: Does 5G Technology Cause Cancer?",
            source="snopes.com",
            url="https://www.snopes.com/fact-check/5g-cellular-cancer-claims/",
            content="Extensive electromagnetic health research by international telecommunication and radiation health bodies demonstrates that 5G non-ionizing signals do not induce carcinogenic DNA breaks.",
            content_hash="hash_5gcancer"
        )
        db.session.add(art5g)
        db.session.commit()

    # 4. Seed 'Climate change hoax'
    s3 = db.session.query(SearchHistory).filter_by(user_id=user.id, query="Climate change hoax").first()
    if not s3:
        s3 = SearchHistory(
            user_id=user.id,
            query="Climate change hoax",
            status="completed",
            search_status="completed",
            summary="Over 97% of actively publishing climate scientists agree that global climate warming trends over the past century are extremely likely due to human activities.",
            fact_check_result="MISINFORMATION DETECTED",
            articles_collected=1,
            processing_time=1.95
        )
        db.session.add(s3)
        db.session.commit()

    art_cc = Article.query.filter_by(search_id=s3.id).first()
    if not art_cc:
        art_cc = Article(
            search_id=s3.id,
            user_id=user.id,
            title="NASA: Scientific Consensus on Global Climate Change",
            source="nasa.gov",
            url="https://climate.nasa.gov/scientific-consensus/",
            content="Multiple studies published in peer-reviewed scientific journals show that climate-warming trends over the past century are human-induced.",
            content_hash="hash_climatenasa"
        )
        db.session.add(art_cc)
        db.session.commit()

    print("Demo data successfully seeded for Liz (researcher_test@example.com)!")
