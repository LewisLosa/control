{
  description = "SengozHome control dashboard and application workers";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = {self, nixpkgs}: let
    systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs systems;
  in {
    packages = forAllSystems (system: let
      pkgs = import nixpkgs {inherit system;};
      node = pkgs.nodejs_22;
      pnpm = pkgs.pnpm_10;

      backend = pkgs.stdenvNoCC.mkDerivation {
        pname = "control-backend";
        version = "0.1.0";
        src = ./.;
        dontBuild = true;
        installPhase = ''
          mkdir -p $out/lib
          cp -r backend $out/lib/backend
        '';
      };

      pythonApp = name: module: pkgs.writeShellApplication {
        inherit name;
        runtimeInputs = [pkgs.python3];
        text = ''
          export PYTHONPATH=${backend}/lib''${PYTHONPATH:+:$PYTHONPATH}
          exec ${pkgs.python3}/bin/python3 -m ${module} "$@"
        '';
      };
    in {
      control-web = pkgs.stdenvNoCC.mkDerivation (finalAttrs: {
        pname = "control-web";
        version = "0.1.0";
        src = ./.;
        nativeBuildInputs = [node pnpm pkgs.pnpmConfigHook];
        pnpmDeps = pkgs.fetchPnpmDeps {
          inherit (finalAttrs) pname version src;
          inherit pnpm;
          fetcherVersion = 4;
          hash = "sha256-CbAlAhIDq+F6/iXKUa/Wr6c9OuKtePk3P5T/eppUlA4=";
        };
        buildPhase = ''
          runHook preBuild
          pnpm run build
          runHook postBuild
        '';
        installPhase = ''
          mkdir -p $out
          cp -r build $out/build
        '';
      });

      music-worker = pythonApp "music-worker" "backend.music.worker";
      music-web = pythonApp "music-web" "backend.music.web";
      av1-worker = pythonApp "av1-worker" "backend.av1.worker";
      av1-api = pythonApp "av1-api" "backend.av1.api";
      av1-enqueue = pythonApp "av1-enqueue" "backend.av1.enqueue";
      av1-encode = pythonApp "av1-encode" "backend.av1.direct";
      arr-auto-import = pythonApp "auto_import" "backend.arr.auto_import";
      music-library-sanitize = pythonApp "music-library-sanitize" "backend.music.library_sanitize";
    });
  };
}
