# Sort video into 3 sections

# # Image dimensions
# IM_WIDTH = 4608  
# IM_HEIGHT = 2592  

# # Define regions for Player 1, Player 2, and Crib
# player1_region = (0, 0, IM_WIDTH // 3, IM_HEIGHT)        # Left 1/3 of the image
# player2_region = (IM_WIDTH // 3, 0, 2 * IM_WIDTH // 3, IM_HEIGHT)  # Middle 1/3
# crib_region = (2 * IM_WIDTH // 3, 0, IM_WIDTH, IM_HEIGHT)  # Right 1/3

# player1_cards = []
# player2_cards = []
# crib_cards = []

# def add_card(player, card):
#     """ Adds detected cards to the correct stack and immediately displays them. """
#     if player == "player1":
#         player1_cards.append(card)
#     elif player == "player2":
#         player2_cards.append(card)
#     elif player == "crib":
#         crib_cards.append(card)
    
#     # Automatically display updated hands
#     display_cards()

# def display_cards():
#     """ Prints the updated hands for each player and the crib. """
#     print("\nUpdated Hands:")
#     print("Player 1's Cards:", player1_cards)
#     print("Player 2's Cards:", player2_cards)
#     print("Crib Cards:", crib_cards)
