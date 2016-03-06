package main

import (
	"bufio"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type POSTInput struct {
	Gists []string
}

func handler(w http.ResponseWriter, r *http.Request) {

	bn := filepath.Base(r.URL.String())
	gistID := strings.TrimSuffix(bn, filepath.Ext(bn))

	if gistID != "/" {

		// A gist_id has been detected in the url, so simply serve the
		// file directly
		http.ServeFile(w, r, fmt.Sprintf("./thumbnails/%s.png", gistID))

	} else {

		// No file is specified in the url so we expect a POST request
		// with the following structure:
		// {"gists": ["<gist_id1>", "<gist_id2>", ..]}

		decoder := json.NewDecoder(r.Body)
		var pi POSTInput
		err := decoder.Decode(&pi)
		if err != nil || len(pi.Gists) == 0 {
			w.WriteHeader(http.StatusInternalServerError)
			w.Write([]byte("cannot parse JSON POST request"))
			return
		}

		gistImageBase64Strings := make(map[string]string)
		for _, gistID := range pi.Gists {
			imgFile, err := os.Open(fmt.Sprintf("./thumbnails/%s.png", gistID))
			defer imgFile.Close()
			if err != nil {
				gistImageBase64Strings[gistID] = "not found"
			} else {
				gistImageBase64Strings[gistID] = "ok"
				fInfo, _ := imgFile.Stat()
				var size int64 = fInfo.Size()
				buf := make([]byte, size)

				// read file content into buffer
				fReader := bufio.NewReader(imgFile)
				fReader.Read(buf)

				// convert the buffer bytes to base64 string - use buf.Bytes() for new image
				gistImageBase64Strings[gistID] = base64.StdEncoding.EncodeToString(buf)
			}
		}

		js, _ := json.Marshal(gistImageBase64Strings)
		w.Header().Set("Content-Type", "application/json")
		w.Write(js)
	}
}

func main() {
	http.HandleFunc("/", handler)
	http.ListenAndServe(":8080", nil)
}
