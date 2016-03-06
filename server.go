package main

import (
	"bufio"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type POSTInput struct {
	Gists []string
}

func handler(w http.ResponseWriter, r *http.Request, servedPath string) {

	ip, _, _ := net.SplitHostPort(r.RemoteAddr)
	bn := filepath.Base(r.URL.String())
	gistID := strings.TrimSuffix(bn, filepath.Ext(bn))

	if gistID != "/" {

		// A gist_id has been detected in the url, so simply serve the
		// file directly
		fnPath := fmt.Sprintf("%s/%s.png", servedPath, gistID)
		if _, err := os.Stat(fnPath); err == nil {
			http.ServeFile(w, r, fnPath)
			fmt.Println(fmt.Sprintf("Served %s to %s", fnPath, ip))
		} else {
			w.WriteHeader(http.StatusNotFound)
			w.Write([]byte(fmt.Sprintf("gist thumbnail %s does not exist", gistID)))
			fmt.Println(fmt.Sprintf("%s requested %s (404)", ip, fnPath))
		}

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
			fmt.Println(fmt.Sprintf("Bad JSON from %s (500)", ip))
			return
		}

		gistImageBase64Strings := make(map[string]string)
		for _, gistID := range pi.Gists {
			imgFile, err := os.Open(fmt.Sprintf("%s/%s.png", servedPath, gistID))
			defer imgFile.Close()
			if err != nil {
				gistImageBase64Strings[gistID] = "not found"
			} else {
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
		fmt.Println(fmt.Sprintf("Served JSON array of %d images to %s", len(gistImageBase64Strings), ip))
	}
}

func main() {

	port := flag.Int("port", 8080, "listening port")
	path := flag.String("path", "./thumbnails", "path of served thumbnail folder")
	flag.Parse()
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		handler(w, r, *path)
	})
	err := http.ListenAndServe(fmt.Sprintf(":%d", *port), nil)
	if err != nil {
		fmt.Println(err)
	}

}
