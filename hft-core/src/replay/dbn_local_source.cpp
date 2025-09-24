#include "hft/core/replay/dbn_local_source.hpp"
#include "hft/core/replay/dbn_reader.hpp"

#include <databento/dbn.hpp>

#include <iostream>

namespace hft::core::replay {

DBNLocalSource::~DBNLocalSource() { close(); }

bool DBNLocalSource::open(const std::string& path) {
    close();
    reader_ = std::make_unique<DBNReader>();
    if (!reader_->open(path)) {
        std::cerr << "Failed to open DBN file: " << path << "\n";
        return false;
    }
    // Optional: print summary
    const auto& md = reader_->metadata();
    std::cout << "DBN opened dataset=" << md.dataset << ", start=" << md.start << ", end=" << md.end << "\n";
    return true;
}

bool DBNLocalSource::next(FeedEvent& out) {
    if (!reader_) return false;

    const databento::Record* rec{nullptr};
    while (reader_->next(rec)) {
        if (!rec) break;
        if (const auto* mbo = rec->GetIf<databento::MboMsg>()) {
            const auto& hdr = mbo->hd;
            out.symbol = std::to_string(hdr.instrument_id);
            out.ts_event_ns = static_cast<std::uint64_t>(hdr.ts_event.time_since_epoch().count());
            out.order_id = mbo->order_id;
            // map side enum to char used by our FeedEvent
            switch (mbo->side) {
                case databento::Side::Ask: out.side = 'S'; break;
                case databento::Side::Bid: out.side = 'B'; break;
                default: out.side = ' '; break;
            }
            out.price_cents = mbo->price; // TODO: apply scaling if needed
            out.qty = static_cast<int>(mbo->size);
            switch (mbo->action) {
                case databento::Action::Add: out.action = FeedAction::Add; break;
                case databento::Action::Cancel: out.action = FeedAction::Cancel; break;
                case databento::Action::Modify: out.action = FeedAction::Replace; out.new_price_cents = mbo->price; out.new_qty = static_cast<int>(mbo->size); break;
                case databento::Action::Trade: out.action = FeedAction::Execute; out.exec_is_aggressor = true; break;
                case databento::Action::Fill: out.action = FeedAction::Execute; out.exec_is_aggressor = false; break;
                case databento::Action::Clear:
                case databento::Action::None: out.action = FeedAction::Unknown; break;
            }
            return true;
        }
        // Skip non-MBO records
    }
    return false; // EOF
}

void DBNLocalSource::close() {
    reader_.reset();
}

} // namespace hft::core::replay


