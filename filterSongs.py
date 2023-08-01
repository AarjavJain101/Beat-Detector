import syncedlyrics

def addToFile(lyrics, provider, song_index_f):
    first_index = lyrics.index("\n")
    second_index = lyrics.index("\n", first_index + 1)
    third_index = lyrics.index("\n", second_index + 1)
    fourth_index = lyrics.index("\n", third_index + 1)
    fifth_index = lyrics.index("\n", fourth_index + 1)
    sixth_index = lyrics.index("\n", fifth_index + 1)
    print(lyrics[:sixth_index])
    print()

    goodFile = None

    check = input("Keep or Stop? (y/n) or S: ")

    if (check == 'y'):
        goodFile = open("Songs_To_Try.txt", "a", encoding="utf-8")
        goodFile.write(f"{provider}: {song}")
        print("Added")
        print()
        return True
    elif check == 'S':
        goodFile = open("Songs_To_Try.txt", "a", encoding="utf-8")
        goodFile.write(f"Stopped: {song_index_f}")
        return 2
    else:
        return False

index = 0
# Go to end of file and see the index we left off at
with open("Songs_To_Try.txt", "r", encoding="utf-8") as file:
    lines = file.readlines()
    if len(lines) != 0:
        last_line = lines[-1]
        index = int(last_line.split(": ")[1])
    else:
        index = 0

# Open song.txt and read lines
with open("songs.txt", "r", encoding="utf-8") as file:
    songs = file.readlines()
    check = False 

    # Separate artist and song name
    for song_index, song in enumerate(songs):
        if song_index < index:
            continue
        else:
            artists, song_name = song.split(" - ")

            # Remove \n from song_name
            song_name = song_name.strip("\n")
            print(f"Artist: {artists}, Song: {song_name}")
            print()

            # Check Lyrics
            lyrics = syncedlyrics.search(f"[{song_name}] [{artists}]", providers=["Musixmatch"])
            if lyrics != None:
                check = addToFile(lyrics, "Musixmatch", song_index)
            if check == 2:
                break
            elif check == False:
                lyrics = syncedlyrics.search(f"[{song_name}] [{artists}]", providers=["NetEase"])
                if lyrics != None:
                    check = addToFile(lyrics, "NetEase", song_index)
                if lyrics == None or check == False:
                    lyrics = syncedlyrics.search(f"[{song_name}] [{artists}]", providers=["Lyricsify"])
                    if lyrics != None:
                        check = addToFile(lyrics, "Lyricsify")
                    if lyrics == None or check == False:
                        lyrics = syncedlyrics.search(f"[{song_name}] [{artists}]", providers=["Megalobiz"])
                        if lyrics != None:
                            check = addToFile(lyrics, "Megalobiz", song_index)
                        elif lyrics == None:
                            print("No Lyrics Found")
                            print()



