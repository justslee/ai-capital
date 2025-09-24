#pragma once

#include <string>
#include <memory>

#include "hft/core/replay/feed_source.hpp"
#include "hft/core/replay/dbn_reader.hpp"

namespace hft::core::replay {

// class DBNReader; // now included above for complete type

// DBN local file source (MBO). Streaming via DBNReader.
class DBNLocalSource : public FeedSource {
public:
    DBNLocalSource() = default;
    ~DBNLocalSource() override;

    bool open(const std::string& path) override;
    bool next(FeedEvent& out) override;
    void close() override;

private:
    std::unique_ptr<DBNReader> reader_;
};

} // namespace hft::core::replay


