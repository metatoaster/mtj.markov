from random import Random


def stub_module_random(testcase_inst, module, seed=0):
    delete = not hasattr(testcase_inst, '_random_mod')
    if delete:
        testcase_inst._random_mod = Random(seed)
    random = testcase_inst._random_mod.random

    def cleanup():
        module.random = original_random
        if delete:
            del testcase_inst._random_mod

    testcase_inst.addCleanup(cleanup)
    original_random, module.random = module.random, random
    return random
