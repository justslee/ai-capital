#pragma once

#include <cstddef>
#include <cstdint>
#include <atomic>
#include <vector>

namespace hft::core {

template <typename T>
class RingBuffer {
public:
    enum class ProducerMode : std::uint8_t { Single, Multi };

    class Writer {
    public:
        Writer() = default;
        explicit Writer(RingBuffer<T>* parent) : parent_(parent) {}

        Writer(const Writer&) = delete;
        Writer& operator=(const Writer&) = delete;
        Writer(Writer&&) = default;
        Writer& operator=(Writer&&) = default;

        bool tryEnqueue(const T& item) { return parent_ ? parent_->tryEnqueue(item) : false; }
        bool tryEnqueue(T&& item) { return parent_ ? parent_->tryEnqueue(std::move(item)) : false; }

    private:
        RingBuffer<T>* parent_{nullptr};
    };

    class Reader {
    public:
        Reader() = default;
        explicit Reader(RingBuffer<T>* parent) : parent_(parent) {}

        Reader(const Reader&) = delete;
        Reader& operator=(const Reader&) = delete;
        Reader(Reader&&) = default;
        Reader& operator=(Reader&&) = default;

        bool tryDequeue(T& out) { return parent_ ? parent_->tryDequeue(out) : false; }
        bool empty() const noexcept { return parent_ ? parent_->empty() : true; }
        std::size_t capacity() const noexcept { return parent_ ? parent_->capacity() : 0; }

    private:
        RingBuffer<T>* parent_{nullptr};
    };

    RingBuffer(std::size_t capacityPowerOfTwo, ProducerMode mode = ProducerMode::Single);
    ~RingBuffer();

    RingBuffer(const RingBuffer&) = delete;
    RingBuffer& operator=(const RingBuffer&) = delete;
    RingBuffer(RingBuffer&&) = delete;
    RingBuffer& operator=(RingBuffer&&) = delete;

    bool tryEnqueue(const T& item);
    bool tryEnqueue(T&& item);

    bool tryDequeue(T& out);

    std::size_t capacity() const noexcept;
    bool empty() const noexcept;
    bool full() const noexcept;

    Writer writer() { return Writer{this}; }
    Reader reader() { return Reader{this}; }

private:
    std::vector<T> buffer_{};
    std::size_t capacity_{};
    std::size_t mask_{};
    ProducerMode mode_{ProducerMode::Single};
    alignas(64) std::atomic<std::uint64_t> head_{0};
    alignas(64) std::atomic<std::uint64_t> tail_{0};
};

} // namespace hft::core

// ---------------------- Template definitions ----------------------
namespace hft::core {
    
template <typename T>
inline RingBuffer<T>::RingBuffer(std::size_t capacityPowerOfTwo, ProducerMode mode)
    : capacity_(capacityPowerOfTwo),
      mask_(capacityPowerOfTwo ? (capacityPowerOfTwo - 1) : 0),
      mode_(mode) {

    buffer_.resize(capacity_);
    head_.store(0, std::memory_order_relaxed);
    tail_.store(0, std::memory_order_relaxed);
}

template <typename T>
inline RingBuffer<T>::~RingBuffer() = default;

template<typename T>
inline bool RingBuffer<T>::tryEnqueue(const T& item) {
    if (mode_ != ProducerMode::Single) {
        return false;
    }

    const std::uint64_t head = head_.load(std::memory_order_relaxed);
    const std::uint64_t tail = tail_.load(std::memory_order_acquire);

    if (head - tail >= capacity_) {
        return false;
    }

    const std::size_t idx = static_cast<std::size_t>(head & static_cast<std::uint64_t>(mask_));
    buffer_[idx] = item; // copy into slot

    head_.store(head + 1, std::memory_order_release);
    return true;
}

template<typename T>
inline bool RingBuffer<T>::tryEnqueue(T&& item) {
    if (mode_ != ProducerMode::Single) {
        return false;
    }
    const std::uint64_t head = head_.load(std::memory_order_relaxed);
    const std::uint64_t tail = tail_.load(std::memory_order_acquire);
    if (head - tail >= capacity_) {
        return false;
    }
    const std::size_t idx = static_cast<std::size_t>(head & static_cast<std::uint64_t>(mask_));
    buffer_[idx] = std::move(item);
    head_.store(head + 1, std::memory_order_release);
    return true;
}

template<typename T>
inline bool RingBuffer<T>::tryDequeue(T& out) {
    const std::uint64_t tail = tail_.load(std::memory_order_relaxed);
    const std::uint64_t head = head_.load(std::memory_order_acquire);
    if (head == tail) {
        return false;
    }
    const std::size_t idx = static_cast<std::size_t>(tail & static_cast<std::uint64_t>(mask_));
    out = std::move(buffer_[idx]);
    tail_.store(tail + 1, std::memory_order_release);
    return true;
}

template<typename T>
inline bool RingBuffer<T>::empty() const noexcept {
    return head_.load(std::memory_order_acquire) == tail_.load(std::memory_order_acquire);
}

template<typename T>
inline bool RingBuffer<T>::full() const noexcept {
    const auto h = head_.load(std::memory_order_acquire);
    const auto t = tail_.load(std::memory_order_acquire);
    return (h - t) >= capacity_;
}

template <typename T>
inline std::size_t RingBuffer<T>::capacity() const noexcept {
    return capacity_;
}


} // namespace hft::core


