add_executable(backtest_sim
    main.cpp
)

target_link_libraries(backtest_sim PRIVATE hftcore)
target_link_libraries(backtest_sim PRIVATE databento::databento)


