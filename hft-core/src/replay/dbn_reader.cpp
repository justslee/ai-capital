#include "hft/core/replay/dbn_reader.hpp"

#include <stdexcept>

namespace hft::core::replay {

bool DBNReader::open(const std::string& path) {
    try {
        store_ = std::make_unique<databento::DbnFileStore>(path.c_str());
        metadata_ = store_->GetMetadata();
        return true;
    } catch (const std::exception&) {
        store_.reset();
        return false;
    }
}

void DBNReader::close() {
    store_.reset();
}

bool DBNReader::next(const databento::Record*& outRecord) {
    if (!store_) return false;
    outRecord = store_->NextRecord();
    return outRecord != nullptr;
}

} // namespace hft::core::replay




