## Questions:

1. Which workloads are the most sensitive to cache parameters? Which parameters are they sensitive to and why?
2. Which processors are the most sensitive to cache size? Why?

### Checklist:

- 2 sweeps
  - cache size
    -- L1D 4KB, L1I 4KB, L2 32KB (DEFAULT)
    -- L1D 8KB, L1I 8KB, L2 32KB (double L1)
    -- L1D 4KB, L1I 4KB, L2 64KB (double L2)
  - cache associative
