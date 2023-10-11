from numpy import random


def generate_normal_random():
    result = random.normal(scale=0.1)
    if result >= -1.0:
        return result
    else:
        return 0.0


def timer(e):
    return e['time']


def generate_micro_batch(num_a: int, num_b: int):
    if num_a % num_b == 0:
        return [num_a // num_b] * num_b
    else:
        return [num_a // num_b] * num_b + [num_a % num_b]
