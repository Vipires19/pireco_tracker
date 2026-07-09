# ADR-001: Gateway separado da API

## Contexto

A plataforma precisa receber milhares de conexões TCP simultâneas de rastreadores veiculares enquanto expõe uma API REST para clientes web e mobile.

## Problema

Unificar gateway TCP e API REST no mesmo processo cria acoplamento entre I/O de rede de baixa latência e requisições HTTP, dificultando escalabilidade independente e aumentando o risco de que operações bloqueantes na API afetem o recebimento de pacotes dos equipamentos.

## Alternativas consideradas

1. **Monólito FastAPI com servidor TCP embutido** — simples, porém escala de forma acoplada.
2. **Gateway TCP separado + API REST** — dois serviços independentes com responsabilidades distintas.
3. **Sidecar por conexão** — complexidade operacional excessiva para a fase inicial.

## Decisão tomada

Adotar um **Gateway TCP dedicado** (`gateway/`) totalmente separado do **Backend FastAPI** (`backend/`).

O gateway é responsável exclusivamente por aceitar conexões, validar o protocolo do equipamento e publicar eventos. O backend expõe API REST e consulta dados persistidos.

## Consequências

- Escalabilidade horizontal independente (mais réplicas de gateway sem afetar a API).
- Deploy e restart do backend não derrubam conexões TCP ativas.
- Necessidade de um barramento de mensagens entre gateway e processadores (Redis Streams).
- Duplicação controlada de configuração entre serviços (mitigada por `.env` compartilhado).
