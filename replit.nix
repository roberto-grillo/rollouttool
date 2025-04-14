{ pkgs }: {
  deps = [
    pkgs.glibcLocales
    pkgs.python310
    pkgs.python310Packages.flask
    pkgs.python310Packages.requests
    pkgs.python310Packages.requests-oauthlib
    pkgs.python310Packages.python-dotenv
    pkgs.python310Packages.flask_sqlalchemy
    pkgs.python310Packages.pandas
    pkgs.python310Packages.openpyxl
  ];
}
