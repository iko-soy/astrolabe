{
  description = "Astrolabe Urbit desk";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          nounPy = pkgs.fetchurl {
            name = "noun.py";
            url = "https://raw.githubusercontent.com/urbit/tools/f9cda82a7699cad0c1c0f8c031a59e93f028e548/pkg/pynoun/noun.py";
            hash = "sha256-vSKQ/UuSmGTANfW5c3I9lQcUFycvqmu5gqysFuP5SAA=";
          };
          ui = pkgs.buildNpmPackage {
            pname = "astrolabe-ui";
            version = "0.3.0";
            src = ./ui;
            nodejs = pkgs.nodejs_22;
            npmDepsHash = "sha256-jCkfgNgBmq0mKjmXBbPwdpzBR/E09OgS9XD6O9hRHfw=";
            makeCacheWritable = true;
            npmFlags = [ "--legacy-peer-deps" ];
            npmBuildScript = "build";

            installPhase = ''
              runHook preInstall
              cp -r dist $out
              runHook postInstall
            '';
          };
        in
        rec {
          inherit ui;
          desk = pkgs.stdenvNoCC.mkDerivation {
            pname = "astrolabe-desk";
            version = "1.0.7";
            dontUnpack = true;
            nativeBuildInputs = [ pkgs.rsync ];

            installPhase = ''
              runHook preInstall
              mkdir -p $out
              rsync -r --copy-links --exclude-from=${./config/ignore_files_on_install.txt} ${./base-desk}/ $out/
              rsync -r --copy-links --exclude-from=${./config/ignore_files_on_install.txt} ${./docs-dev-desk}/ $out/
              rsync -r --copy-links --exclude-from=${./config/ignore_files_on_install.txt} ${./desk}/ $out/
              runHook postInstall
            '';
          };
          glob = pkgs.stdenvNoCC.mkDerivation {
            pname = "astrolabe-glob";
            version = "0.3.0";
            dontUnpack = true;
            nativeBuildInputs = [
              (pkgs.python3.withPackages (ps: [ ps.mmh3 ps.bitstring ]))
            ];

            installPhase = ''
              runHook preInstall
              mkdir -p $TMPDIR/pynoun
              ln -s ${nounPy} $TMPDIR/pynoun/noun.py
              PYTHONPATH=$TMPDIR/pynoun python ${./bin/make_glob.py} ${ui} $out
              runHook postInstall
            '';
          };
          default = desk;
        });
    };
}
