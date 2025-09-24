#pragma once

#include <cstdint>
#include <string>
#include <memory>

#include <databento/dbn.hpp>
#include <databento/dbn_file_store.hpp>

namespace hft::core::replay {

// Thin wrapper over Databento's DbnFileStore for local DBN(.zst) iteration
class DBNReader {
public:
    DBNReader() = default;
    ~DBNReader() = default;

    DBNReader(const DBNReader&) = delete;
    DBNReader& operator=(const DBNReader&) = delete;

    bool open(const std::string& path);
    void close();

    // Advance to next record; returns false on EOF
    bool next(const databento::Record*& outRecord);

    const databento::Metadata& metadata() const { return metadata_; }
    bool isOpen() const noexcept { return static_cast<bool>(store_); }

private:
    std::unique_ptr<databento::DbnFileStore> store_;
    databento::Metadata metadata_{};
};

} // namespace hft::core::replay


 