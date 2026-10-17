// -*- c-basic-offset: 4; indent-tabs-mode: nil -*-
#ifndef REORDER_BITMAP_H
#define REORDER_BITMAP_H

#include <vector>
#include <cstdint>
#include <cassert>

// Receive-side reorder state: one uint8_t per sequence number, indexed
// modulo MaxSize (as ModularVector<uint8_t, MaxSize> did).
//
// Instead of always holding MaxSize bytes, storage is allocated only when a
// non-zero value is first written, and grows (in powers of two, up to
// MaxSize) to cover the furthest out-of-order packet seen. A flow that never
// receives packets out of order uses no storage at all.
//
// Requirement (true for the receiver's out-of-order bitmap): every non-zero
// entry is >= base, where base is the receiver's cumulative ack point. The
// owner keeps base up to date with set_base(). Under that requirement get()
// returns exactly what ModularVector<uint8_t, MaxSize> would have returned,
// including wrap-around beyond MaxSize.
template <unsigned MaxSize>
class ReorderBitmap {
    static_assert(MaxSize && !(MaxSize & (MaxSize - 1)), "MaxSize must be a power of 2");
    static constexpr unsigned MinSize = 64;

   public:
    ReorderBitmap() : _base(0) {}

    uint8_t get(uint64_t idx) const {
        if (offset(idx) >= _buf.size())
            return 0;  // outside the stored window: never written, so 0
        return _buf[idx & (_buf.size() - 1)];
    }

    void set(uint64_t idx, uint8_t value) {
        uint64_t off = offset(idx);
        if (off >= _buf.size()) {
            if (value == 0)
                return;  // already 0
            grow(off);
        }
        _buf[idx & (_buf.size() - 1)] = value;
    }

    // all entries below base are 0 (they have been cumulatively acked)
    void set_base(uint64_t base) {
        assert(base >= _base);
        _base = base;
    }

    // number of non-zero entries (packets held out of order)
    uint32_t count_nonzero() const {
        uint32_t count = 0;
        for (uint8_t v : _buf)
            if (v)
                count++;
        return count;
    }

    size_t allocated_size() const { return _buf.size(); }

   private:
    // distance of idx from base, wrapped like a MaxSize ring
    uint64_t offset(uint64_t idx) const { return (idx - _base) & (MaxSize - 1); }

    // make room for offset off from base, moving existing entries to their
    // slots in the larger buffer
    void grow(uint64_t off) {
        size_t new_size = _buf.empty() ? MinSize : _buf.size();
        while (new_size <= off)
            new_size *= 2;
        assert(new_size <= MaxSize);

        std::vector<uint8_t> new_buf(new_size, 0);
        for (size_t i = 0; i < _buf.size(); i++) {
            uint64_t idx = _base + i;
            new_buf[idx & (new_size - 1)] = _buf[idx & (_buf.size() - 1)];
        }
        _buf.swap(new_buf);
    }

    uint64_t _base;
    std::vector<uint8_t> _buf;  // size is 0 or a power of 2 <= MaxSize
};

#endif
