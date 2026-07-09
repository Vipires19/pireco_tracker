# Protocolos Suportados — Fase 0.5

## Visão Geral

O **Gateway** é o único serviço que conhece protocolos de rastreadores. Todos os demais serviços consomem objetos de domínio protocolo-agnósticos via Redis Streams.

```text
Bytes TCP (GT06) → Gateway/protocol → Domain Objects → Redis Streams → Worker
```

---

## GT06 / J16 (Concox)

Compatível com rastreadores **J16 Pro**, **J16 Ultra** e demais clones GT06.

### Pacotes implementados (Fase 0.5)

| Protocolo | Código | Direção | Descrição |
|-----------|--------|---------|-----------|
| Login | `0x01` | Device → Server | Identificação por IMEI (8 bytes BCD) |
| Heartbeat | `0x13` | Device → Server | Keep-alive + status terminal |
| GPS Location | `0x12` | Device → Server | Posição GPS (lat/lon/speed/course) |

### Estrutura do frame (pacote curto)

```text
[0x78 0x78] [length] [protocol] [payload...] [serial 2B] [CRC 2B] [0x0D 0x0A]
```

- **CRC**: CRC-ITU (X25) sobre `length + protocol + payload + serial`
- **ACK**: `0x78 0x78 0x05 [protocol] [serial] [CRC] 0x0D 0x0A`

### Módulos do Gateway

| Arquivo | Responsabilidade |
|---------|------------------|
| `protocol/constants.py` | Códigos de protocolo |
| `protocol/crc.py` | Validação CRC-ITU |
| `protocol/parser.py` | Extração e validação de frames |
| `protocol/encoder.py` | ACK e builders (simulador) |
| `protocol/packets.py` | Estruturas e decodificação GPS/IMEI |
| `domain/mapper.py` | GT06 → objetos de domínio |

### Objetos de domínio gerados

| Pacote GT06 | Objeto de domínio | `message_type` |
|-------------|-------------------|----------------|
| Login | `DeviceConnection` | `connection` |
| Heartbeat | `DeviceHeartbeat` | `heartbeat` |
| GPS | `DevicePosition` | `position` |
| Disconnect | `DeviceConnection` | `connection` |

### Contrato Redis Stream (`tracker:events`)

Campos publicados (protocolo-agnósticos):

```json
{
  "message_type": "position",
  "tracker_imei": "867686031234567",
  "latitude": "-23.550520",
  "longitude": "-46.633308",
  "speed_kmh": "45.0",
  "course_degrees": "180",
  "gps_time": "2026-06-30T12:00:00+00:00",
  "received_at": "2026-06-30T12:00:01+00:00",
  "published_at": "2026-06-30T12:00:01+00:00",
  "connection_id": "uuid",
  "remote_ip": "127.0.0.1:5023",
  "source_protocol": "gt06"
}
```

> `source_protocol` é apenas para observabilidade. O Worker **não** usa este campo em regras de negócio.

---

## Protocolos futuros

| Protocolo | Status | Ação necessária |
|-----------|--------|-----------------|
| Teltonika | Planejado | Novo módulo `protocol/teltonika/` + mapper |
| Queclink | Planejado | Novo módulo `protocol/queclink/` + mapper |
| JT808 | Planejado | Novo módulo `protocol/jt808/` + mapper |

Nenhuma alteração no Backend ou Worker será necessária — apenas novos mappers no Gateway produzindo os mesmos objetos de domínio.

---

## Simulador

```bash
python scripts/gt06_simulator.py --host localhost --port 5023 --imei 867686031234567
```

Envia sequência: Login → Heartbeat → GPS → Disconnect.
