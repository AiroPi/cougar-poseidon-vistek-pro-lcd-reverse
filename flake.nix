{
  description = "Cougar LCD display control on Linux";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs =
    inputs@{ self, flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      perSystem =
        { pkgs, self', ... }:
        {
          packages.cougar-lcd = pkgs.python3Packages.buildPythonPackage {
            pname = "cougar-lcd";
            version = "0.0.1";
            pyproject = true;
            src = ./.;
            build-system = [
              pkgs.python3Packages.hatchling
            ];
            dependencies = [
              pkgs.python3Packages.pyusb
            ];
          };

          packages.cougar-lcd-overlay =
            let
              pythonEnv = pkgs.python3.withPackages (
                ps: with ps; [
                  self'.packages.cougar-lcd
                  pynvml
                  lxml
                  psutil
                ]
              );
            in
            pkgs.stdenv.mkDerivation {
              pname = "cougar-lcd-overlay-daemon";
              version = "0.0.1";
              src = ./examples/stats;

              nativeBuildInputs = [ pkgs.makeWrapper ];

              installPhase = ''
                runHook preInstall

                mkdir -p $out/bin $out/share/cougar-lcd-overlay-daemon
                cp main.py overlay_svg.py $out/share/cougar-lcd-overlay-daemon/

                makeWrapper ${pythonEnv}/bin/python3 $out/bin/cougar-lcd-overlay-daemon \
                  --add-flags "$out/share/cougar-lcd-overlay-daemon/main.py" \
                  --prefix PATH : "${pkgs.lib.makeBinPath [ pkgs.resvg ]}"

                runHook postInstall
              '';
            };

          devShells.default = pkgs.mkShell {
            packages = [
              (pkgs.python3.withPackages (ps: [ self'.packages.cougar-lcd ]))
            ];
          };
        };

      flake = {
        nixosModules.cougar-lcd-overlay =
          {
            pkgs,
            ...
          }:
          {
            services.udev.extraRules = ''
              SUBSYSTEM=="usb", ATTR{idVendor}=="1d6b", ATTR{idProduct}=="0110", MODE="0660", GROUP="users"
            '';

            systemd.services.cougar-lcd-daemon = {
              description = "Cougar LCD overlay daemon";
              wantedBy = [ "multi-user.target" ];

              serviceConfig = {
                ExecStart = "${self.packages.${pkgs.system}.cougar-lcd-overlay}/bin/cougar-lcd-overlay-daemon";
                User = "pi";  # TODO: make this configuration
                Restart = "on-failure";
              };
            };
          };
      };
    };
}
