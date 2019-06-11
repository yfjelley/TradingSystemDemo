import os
import sys
import traceback
from functools import wraps
from multiprocessing import Process, Queue
import random
from multiprocessing import Process, Queue
import time

def my_func_1(*arg):
    res = 0
    difficulty = 500
    while res != 30:
        randm0 = random.randint(1, difficulty)
        randm1 = random.randint(1, difficulty)
        randm2 = random.randint(1, difficulty)
        res = randm0 + randm1 + randm2
        print('1111111111: sleeping')
        time.sleep(0.01)
    return randm0, randm1, randm2

def my_func_2(*arg):
    res = 0
    difficulty = 500
    while res != 30:
        randm0 = random.randint(1, difficulty)
        randm1 = random.randint(1, difficulty)
        randm2 = random.randint(1, difficulty)
        print('2222: sleeping')
        time.sleep(0.01)
        res = randm0 + randm1 + randm2
    return randm0, randm1, randm2

if __name__ == '__main__':
    p1 = Process(target=my_func_1, args=([111]))
    p2 = Process(target=my_func_2, args=([222]))
    p1.start()
    p2.start()
    p1.join() # this blocks until the process terminates
    p2.join()
    


