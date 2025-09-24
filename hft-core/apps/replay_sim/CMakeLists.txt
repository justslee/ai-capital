add_executable(replay_sim
    main.cpp
)

target_link_libraries(replay_sim PRIVATE hftcore)
target_link_libraries(replay_sim PRIVATE databento::databento)




