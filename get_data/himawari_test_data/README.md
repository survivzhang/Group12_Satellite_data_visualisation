# Automatic Authentication with `.netrc`

To avoid entering your NASA Earthdata credentials every time when using **earthaccess**, you can configure a `.netrc` file for automatic authentication.

---

## Steps

### 1. Create a `.netrc` file
Create a file named `.netrc` in your **home directory**:  

- **Linux / Mac**: `~/.netrc`  
- **Windows**: `%USERPROFILE%\.netrc`  

---

### 2. Add your credentials
Open the `.netrc` file and add the following content (replace with your own username and password):  

```txt
machine urs.earthdata.nasa.gov
    login <your-username>
    password <your-password>
