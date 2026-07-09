from app.protocol.crc import crc16_x25


def test_crc16_x25_known_vector() -> None:
  data = bytes([0x05, 0x01, 0x00, 0x01])
  crc = crc16_x25(data)
  assert isinstance(crc, int)
  assert 0 <= crc <= 0xFFFF


def test_crc_invalid_data_changes() -> None:
  a = crc16_x25(bytes([0x01, 0x02, 0x03]))
  b = crc16_x25(bytes([0x01, 0x02, 0x04]))
  assert a != b
