#include "hft/core/replay/replay_driver.hpp"

#include <exception>
#include <iostream>

int main(int argc, char** argv) {
    try {
        if (argc < 2) {
            std::cerr << "Usage: replay_sim <path-to-dbz-or-dbn> [speed]\n";
            return 2;
        }
        const std::string path = argv[1];
        const double speed = (argc >= 3) ? std::stod(argv[2]) : 1.0;

        hft::core::replay::ReplayDriver driver;
        driver.run(path, speed);

        std::cout << "Replay completed for: " << path << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}




