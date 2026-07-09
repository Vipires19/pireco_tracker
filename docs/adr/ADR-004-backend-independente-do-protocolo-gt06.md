# ADR-004: Backend independente do protocolo GT06

## Contexto

A plataforma inicia com rastreadores GT06, mas a roadmap inclui Teltonika, Queclink e JT808. O backend não deve acumular dívida técnica de protocolos específicos.

## Problema

Na Fase 0, eventos eram publicados com campos como `protocol_number`, `payload_hex` e `raw_hex`, acoplando consumidores ao formato binário GT06 e exigindo parsing no backend para cada novo protocolo.

## Alternativas consideradas

1. **Backend parseia bytes GT06** — viola separação de responsabilidades.
2. **Biblioteca compartilhada de protocolo** — acoplamento entre serviços via imports internos.
3. **Gateway traduz para objetos de domínio protocolo-agnósticos** — backend consome contrato estável.

## Decisão tomada

O **gateway** é o único serviço que conhece GT06. Ele transforma pacotes em objetos de domínio:

- `DevicePosition`
- `DeviceHeartbeat`
- `DeviceEvent`
- `DeviceConnection`

Esses objetos são serializados no Redis Stream com campo `message_type`. O **backend** e o **worker** consomem apenas esse contrato, sem CRC, parsing binário ou tipos de pacote GT06.

## Consequências

- Adicionar Teltonika/Queclink exige apenas novo módulo de protocolo no gateway + mapper para os mesmos objetos de domínio.
- Backend e worker permanecem inalterados ao trocar ou adicionar protocolos.
- O campo `source_protocol` existe apenas para observabilidade, não para lógica de negócio.
- Testes de protocolo ficam isolados no gateway.
