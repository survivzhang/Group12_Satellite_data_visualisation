1. To simplify authentication when using earthaccess, I configured a .netrc file.
This allows automatic login without manually entering your NASA Earthdata username and password each time.

2. Create a file named .netrc in your home directory (e.g., ~/.netrc on Linux/Mac, %USERPROFILE%\.netrc on Windows).

3. Add the following content (replace with your own credentials):

machine urs.earthdata.nasa.gov
    login <your-username>
    password <your-password>

4. Once configured, earthaccess will automatically use these credentials for authentication.