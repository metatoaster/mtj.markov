# -*- coding: utf-8 -*-


class XorShift128(object):
    """
    Predictable pseudonumber generator for testing.
    """

    overflow = (2 ** 32)

    def __init__(self, x=126789834, y=762898365, z=798124191, w=169030803):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
        self.cycle = 0

    def __call__(self):
        self.cycle += 1
        t = self.x ^ (self.x << 11)
        t = t ^ (t << 8)
        self.x, self.y, self.z = self.y, self.z, self.w
        self.w = self.w ^ (self.w >> 19)
        self.w = (self.w ^ t) & (self.overflow - 1)
        return self.w / float(self.overflow)

