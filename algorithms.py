from dataclasses import dataclass
from typing import Callable, List, Any, Optional, Tuple
import time

@dataclass
class SortMetrics:
    algorithm: str
    time_ms: float
    comparisons: Optional[int]
    swaps_or_moves: Optional[int]
    n: int

@dataclass
class SearchMetrics:
    algorithm: str
    time_ms: float
    comparisons: int
    n: int
    details: str = ""

# -------------------------------
# Helper to extract key once
# -------------------------------
def _decorate(data: List[Any], key: Callable[[Any], Any]):
    return [(key(x), x) for x in data]

def _undecorate(decorated: List[tuple]):
    return [x[1] for x in decorated]

# -------------------------------
# Bubble Sort (in-place)
# -------------------------------
def bubble_sort(data: List[Any], key: Callable[[Any], Any], reverse: bool=False) -> Tuple[List[Any], SortMetrics]:
    a = list(data)
    n = len(a)
    comps = 0
    swaps = 0
    t0 = time.perf_counter()
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            k1 = key(a[j]); k2 = key(a[j+1])
            comps += 1
            if (k1 > k2 and not reverse) or (k1 < k2 and reverse):
                a[j], a[j+1] = a[j+1], a[j]
                swaps += 1
                swapped = True
        if not swapped:
            break
    dt = (time.perf_counter() - t0) * 1000
    return a, SortMetrics("bubble", dt, comps, swaps, n)

# -------------------------------
# Selection Sort (in-place, unstable)
# -------------------------------
def selection_sort(data: List[Any], key: Callable[[Any], Any], reverse: bool=False) -> Tuple[List[Any], SortMetrics]:
    a = list(data)
    n = len(a)
    comps = 0
    swaps = 0
    t0 = time.perf_counter()
    for i in range(n):
        idx = i
        for j in range(i+1, n):
            k_best = key(a[idx]); k_j = key(a[j])
            comps += 1
            better = (k_j > k_best) if reverse else (k_j < k_best)
            if better:
                idx = j
        if idx != i:
            a[i], a[idx] = a[idx], a[i]
            swaps += 1
    dt = (time.perf_counter() - t0) * 1000
    return a, SortMetrics("selection", dt, comps, swaps, n)

# -------------------------------
# Insertion Sort (stable)
# -------------------------------
def insertion_sort(data: List[Any], key: Callable[[Any], Any], reverse: bool=False) -> Tuple[List[Any], SortMetrics]:
    a = list(data)
    n = len(a)
    comps = 0
    moves = 0
    t0 = time.perf_counter()
    for i in range(1, n):
        item = a[i]
        k_item = key(item)
        j = i - 1
        while j >= 0:
            comps += 1
            cond = key(a[j]) > k_item if not reverse else key(a[j]) < k_item
            if cond:
                a[j+1] = a[j]
                moves += 1
                j -= 1
            else:
                break
        a[j+1] = item
    dt = (time.perf_counter() - t0) * 1000
    return a, SortMetrics("insertion", dt, comps, moves, n)

# -------------------------------
# Quick Sort (not stable)
# -------------------------------
def _qs(a, lo, hi, key, reverse, counter):
    if lo >= hi:
        return
    pivot = key(a[(lo+hi)//2])
    i, j = lo, hi
    while i <= j:
        while True:
            counter['comparisons'] += 1
            if (key(a[i]) < pivot and not reverse) or (key(a[i]) > pivot and reverse):
                i += 1
            else:
                break
        while True:
            counter['comparisons'] += 1
            if (key(a[j]) > pivot and not reverse) or (key(a[j]) < pivot and reverse):
                j -= 1
            else:
                break
        if i <= j:
            a[i], a[j] = a[j], a[i]
            counter['swaps'] += 1
            i += 1
            j -= 1
    if lo < j: _qs(a, lo, j, key, reverse, counter)
    if i < hi: _qs(a, i, hi, key, reverse, counter)

def quick_sort(data: List[Any], key: Callable[[Any], Any], reverse: bool=False) -> Tuple[List[Any], SortMetrics]:
    a = list(data)
    n = len(a)
    counter = {'comparisons': 0, 'swaps': 0}
    t0 = time.perf_counter()
    if n:
        _qs(a, 0, n-1, key, reverse, counter)
    dt = (time.perf_counter() - t0) * 1000
    return a, SortMetrics("quicksort", dt, counter['comparisons'], counter['swaps'], n)

# -------------------------------
# Merge Sort (stable)
# -------------------------------
def _merge(left, right, key, reverse, counter):
    i = j = 0
    merged = []
    while i < len(left) and j < len(right):
        counter['comparisons'] += 1
        lkey = key(left[i]); rkey = key(right[j])
        if (lkey <= rkey and not reverse) or (lkey >= rkey and reverse):
            merged.append(left[i]); i += 1
        else:
            merged.append(right[j]); j += 1
        counter['moves'] += 1
    while i < len(left):
        merged.append(left[i]); i += 1; counter['moves'] += 1
    while j < len(right):
        merged.append(right[j]); j += 1; counter['moves'] += 1
    return merged

def _ms(a, key, reverse, counter):
    n = len(a)
    if n <= 1: return a
    mid = n // 2
    left = _ms(a[:mid], key, reverse, counter)
    right = _ms(a[mid:], key, reverse, counter)
    return _merge(left, right, key, reverse, counter)

def merge_sort(data: List[Any], key: Callable[[Any], Any], reverse: bool=False) -> Tuple[List[Any], SortMetrics]:
    a = list(data)
    n = len(a)
    counter = {'comparisons': 0, 'moves': 0}
    t0 = time.perf_counter()
    a = _ms(a, key, reverse, counter)
    dt = (time.perf_counter() - t0) * 1000
    return a, SortMetrics("mergesort", dt, counter['comparisons'], counter['moves'], n)

# -------------------------------
# Built-in Timsort (Python's sorted)
# -------------------------------
def builtin_timsort(data: List[Any], key: Callable[[Any], Any], reverse: bool=False) -> Tuple[List[Any], SortMetrics]:
    t0 = time.perf_counter()
    out = sorted(data, key=key, reverse=reverse)
    dt = (time.perf_counter() - t0) * 1000
    # Comparisons/moves not available; leave as None
    return out, SortMetrics("timsort(builtin)", dt, None, None, len(data))

# -------------------------------
# Search algorithms
# -------------------------------
def linear_search_range(data: List[Any], key: Callable[[Any], Any], target: Any, mode: str="==") -> Tuple[List[Any], SearchMetrics]:
    """
    mode: one of '==', '<=', '>='
    Returns all matching items for the condition key(x) mode target
    """
    comps = 0
    t0 = time.perf_counter()
    res = []
    for x in data:
        k = key(x)
        comps += 1
        ok = False
        if mode == "==":
            ok = (k == target)
        elif mode == "<=":
            ok = (k <= target)
        elif mode == ">=":
            ok = (k >= target)
        else:
            raise ValueError("Invalid mode for linear search")
        if ok:
            res.append(x)
    dt = (time.perf_counter() - t0) * 1000
    return res, SearchMetrics("linear", dt, comps, len(data), details=f"mode {mode}")

def _bisect_left(data: List[Any], key: Callable[[Any], Any], target: Any, comparisons: list):
    lo, hi = 0, len(data)
    while lo < hi:
        mid = (lo + hi) // 2
        comparisons[0] += 1
        if key(data[mid]) < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

def _bisect_right(data: List[Any], key: Callable[[Any], Any], target: Any, comparisons: list):
    lo, hi = 0, len(data)
    while lo < hi:
        mid = (lo + hi) // 2
        comparisons[0] += 1
        if key(data[mid]) <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo

def binary_search_range_sorted(data: List[Any], key: Callable[[Any], Any], target: Any, mode: str="==") -> Tuple[List[Any], SearchMetrics]:
    """
    data MUST already be sorted by the same key in non-decreasing order.
    mode: '==', '<=', '>='
    """
    comps = [0]
    t0 = time.perf_counter()
    if mode == "==":
        left = _bisect_left(data, key, target, comps)
        right = _bisect_right(data, key, target, comps)
        res = data[left:right]
        details = f"exact matches for {target}"
    elif mode == "<=":
        right = _bisect_right(data, key, target, comps)
        res = data[:right]
        details = f"<= {target}"
    elif mode == ">=":
        left = _bisect_left(data, key, target, comps)
        res = data[left:]
        details = f">= {target}"
    else:
        raise ValueError("Invalid mode for binary search")
    dt = (time.perf_counter() - t0) * 1000
    return res, SearchMetrics("binary", dt, comps[0], len(data), details=details)

# -------------------------------
# Dispatcher helpers
# -------------------------------
SORTERS = {
    "timsort": builtin_timsort,
    "bubble": bubble_sort,
    "selection": selection_sort,
    "insertion": insertion_sort,
    "quicksort": quick_sort,
    "mergesort": merge_sort,
}

def sort_list(algo: str, data: List[Any], key: Callable[[Any], Any], reverse: bool=False):
    algo = algo.lower()
    if algo not in SORTERS:
        raise ValueError(f"Unknown sort algorithm: {algo}")
    return SORTERS[algo](data, key, reverse)

def search_by_value(algo: str, data: List[Any], key: Callable[[Any], Any], target: Any, mode: str="==", assume_sorted=False):
    algo = algo.lower()
    if algo == "linear":
        return linear_search_range(data, key, target, mode)
    elif algo == "binary":
        if not assume_sorted:
            raise ValueError("Binary search requires pre-sorted data by the same key.")
        return binary_search_range_sorted(data, key, target, mode)
    else:
        raise ValueError(f"Unknown search algorithm: {algo}")
