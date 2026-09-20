# Размеры ордеров и капитал

**Статус: ПОДТВЕРЖДЁННЫЕ ПРИНЦИПЫ / ОТКРЫТА ТОЧНАЯ ФОРМУЛА DYNAMIC SIZING**

Grid Sizing отвечает на вопрос: какой объём должен иметь будущий Grid Order.

## Initial sizing

При запуске сетки sizing может быть ручным или автоматически сгенерированным. Для Auto Grid задаются исходный размер/номинал и Martingale coefficient. Это создаёт первоначальную относительную кривую объёмов.

Martingale относится к sizing, а не к Grid Geometry.

## Capital Allocation Policy

Для стратегии задаются Long allocation %, Short allocation % и Reserve %.

Эти проценты являются постоянной policy текущей конфигурации и применяются повторно при каждом restructuring. Процент фиксирован до изменения настройки трейдером, абсолютный денежный бюджет динамичен.

При изменении актуальной капиталовой базы абсолютные Long/Short/Reserve суммы пересчитываются по тем же процентам.

## Dynamic sizing

После события, изменившего factual state или капитал сетки, будущие неисполненные qty могут быть пересчитаны:

Fresh capital state → apply Long/Short/Reserve % → current side budget → preserve geometry → recalculate eligible future qty → new Grid Revision.

Filled qty никогда не изменяется задним числом.

## Capital state

Перерасчёт должен работать от актуального состояния аккаунта и учитывать текущий результат, включая realized и unrealized компоненты в доступной капиталовой базе. Точная привязка к конкретным полям Bybit и обработка funding/fees должны быть формально зафиксированы перед автономным исполнением.

## Exchange constraints

Каждый итоговый qty проходит minOrderQty, qtyStep и minNotionalValue; цена проходит tickSize. Ограничения читаются per instrument и не хардкодятся глобально.
