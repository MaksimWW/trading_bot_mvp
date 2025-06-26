import asyncio


async def detailed_debug():
    print("🔍 Детальная отладка TradingEngine...")
    engine = TradingEngine()

    print("\n1. Тестируем технический анализ:")
    tech_result = await engine.technical_analyzer.analyze_ticker("SBER")
    print(f"   Результат: {tech_result}")

    print("\n2. Тестируем анализ новостей:")
    news_result = await engine.news_analyzer.analyze_ticker_news("SBER", include_sentiment=True)
    print(f"   Результат: {news_result}")

    print("\n3. Тестируем расчет комбинированного сигнала:")
    technical_score = tech_result.get("combined_signal", 0.0)
    news_score = (
        news_result["sentiment"]["sentiment_score"] if news_result.get("sentiment") else 0.0
    )
    combined_score = (technical_score * 0.6) + (news_score * 0.4)
    print(f"   Technical score: {technical_score}")
    print(f"   News score: {news_score}")
    print(f"   Combined score: {combined_score}")

    print("\n4. Тестируем интерпретацию сигнала:")
    direction, strength = engine._interpret_signal(combined_score)
    print(f"   Direction: {direction}")
    print(f"   Strength: {strength.value}")

    print("\n5. Тестируем расчет уверенности:")
    confidence = engine._calculate_confidence(tech_result, news_result)
    print(f"   Confidence: {confidence}")

    print("\n6. Проверяем фильтры:")
    print(f"   Min signal strength: {engine.min_signal_strength.value}")
    print(f"   Min confidence: {engine.min_confidence}")
    print(f'   Strength check: {strength.value not in ["VERY_WEAK", "WEAK"]}')
    print(f"   Confidence check: {confidence >= engine.min_confidence}")

    if strength.value in ["VERY_WEAK", "WEAK"]:
        print("   ❌ Сигнал отклонен: слишком слабый")
    elif confidence < engine.min_confidence:
        print("   ❌ Сигнал отклонен: низкая уверенность")
    else:
        print("   ✅ Сигнал должен пройти фильтры")


asyncio.run(detailed_debug())
