

def apply_on_axis_0_n_times(data, method, n_times):

    for _ in range(n_times):
        data = method(data, axis=0)
    return data
