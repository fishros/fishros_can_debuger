
def decompose_byte(byte, decomposition_pattern):
    result = []
    index = 0

    for size in decomposition_pattern:
        bits = int(size)
        # print(bits, index)
        if index + bits <= 8:
            # Extract bits from low to high
            extracted_bits = (byte >> index) & ((1 << bits) - 1)
            result.append(extracted_bits)
            index += bits
        else:
            raise ValueError("Invalid decomposition pattern or byte size")

    return tuple(result)


def compose_byte(bit_values, composition_pattern):
    byte = 0
    index = 0

    for value, size in zip(bit_values, composition_pattern):
        bits = int(size)
        if value >= (1 << bits):
            raise ValueError("Bit value exceeds the specified bit size")
        byte |= (value & ((1 << bits) - 1)) << index
        index += bits

    if index > 8:
        raise ValueError("Composition pattern exceeds byte size")

    return byte

# Example usage
bit_values = (3, 1, 1)  # Example bit values
composition_pattern = (2, 3, 3)  # Corresponding sizes of each bit value



composed_byte = compose_byte((1, 0, 1, 1, 1, 1, 1, 1), "11111111")
print(f"Composed byte: {composed_byte}")
print(decompose_byte(composed_byte,"11111111"))