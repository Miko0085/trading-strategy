# Известные риски

## Martingale и глубокий exposure

Рост planned qty на глубоких уровнях ускоряет использование маржи при сильном однонаправленном движении. Dynamic sizing всегда должен проходить через текущий Long/Short/Reserve allocation guard.

## Низкая ликвидность и partial fill

Крупный глубокий Limit Order может исполниться только частично. Основные риски: ошибочный TP от configured_qty, попытка закрыть больше factual open_qty, residual ниже minOrderQty/minNotionalValue и рассинхронизация TP при дополнительных fills.

Базовый invariant: close qty никогда не превышает factual open_qty.

## Tail risk

Последовательное исполнение всё более крупных уровней против сильного движения может быстро увеличить exposure и сократить запас available margin.

## Account-level risk

Несколько активов используют общий ресурс аккаунта. Независимые grid strategies нельзя оценивать только symbol-by-symbol.

## Trailing churn

Слишком частый trailing может создать постоянный cancel/replace поток. Нужен формальный trigger/step.

## Stop Loss

Stop Loss остаётся открытым вопросом и не считается обязательным базовым правилом.

## Ручное вмешательство

Внешние изменения через Bybit требуют reconciliation и подтверждения, а не автоматической стратегической перестройки.
