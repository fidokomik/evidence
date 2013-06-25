#!/usr/bin/perl
# Author: Petr Vileta, 2012
# License: WTFPL - Do What The Fuck You Want To Public License, http://sam.zoy.org/wtfpl/

use strict;
use DBI;

require "init.pl";

# our $rp=25; #skupina Republikove predsednictvo
# our $rv=29; #skupina Republikovy vybor

our ($db,$dbhost,$dbport,$dbuser,$dbpw)=connect_db();
our $dbh = DBI->connect("DBI:mysql:$db:$dbhost:$dbport",$dbuser,$dbpw) or die "Can't connect: $DBI::errstr\n";
$dbh->do("SET character_set_connection=utf8");
$dbh->do("SET character_set_client=utf8");
$dbh->do("SET character_set_results=utf8");
our $kstopks=get_setup('ks_to_pks','text'); # prevodnik cisla KS na cislo PKS
$kstopks=~s/(\d+)=(\d+)[^\d]+/$1=$2 /sg;

# nacist cisla skupin, ktere se maji proverit
my @groups=split(/,/,get_setup('groups_to_log','text'));
my $sth1=$dbh->prepare("SELECT `user_id`,`group_leader`,`group_name` FROM `phpbb_user_group`
  	LEFT JOIN `phpbb_groups` ON (`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
		WHERE `phpbb_user_group`.`group_id`=?");
my $sth1a=$dbh->prepare("SELECT `group_leader` FROM `phpbb_user_group`
		WHERE `user_id`=? AND `group_id`=?");
my $sth1b=$dbh->prepare("SELECT `group_leader` FROM `phpbb_user_group`
		WHERE `group_leader` > 0 AND `user_id`=? AND `group_id`=?");
my $sth2=$dbh->prepare("SELECT `user_id`,`vedouci`,`funkce` FROM `evidence_clenstvi`
		WHERE `user_id`=? AND `group_id`=? AND ISNULL(`datum_do`)");
my $sth2a=$dbh->prepare("SELECT `user_id`,`vedouci`,`funkce` FROM `evidence_clenstvi`
		WHERE `user_id`=? AND `group_id`=? AND NOT ISNULL(`datum_do`)");
my $sth3=$dbh->prepare("INSERT INTO `evidence_clenstvi` SET
		`user_id`=?,`group_id`=?,`vedouci`=?,`funkce`=?,`datum_od`=?");
my $sth4=$dbh->prepare("SELECT `user_id`,`vedouci`,`funkce` FROM `evidence_clenstvi`
		WHERE `group_id`=? AND ISNULL(`datum_do`)");
my $sth5=$dbh->prepare("SELECT `user_id`,`group_leader`,`group_name` FROM `phpbb_user_group`
		LEFT JOIN `phpbb_groups` ON (`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
		WHERE `user_id`=? AND `phpbb_user_group`.`group_id`=?");
my $sth6=$dbh->prepare("UPDATE `evidence_clenstvi` SET
		`datum_do`=NOW() WHERE `user_id`=? AND `group_id`=?");
my $sth7=$dbh->prepare("SELECT `pf_vznikclenstvi` FROM `phpbb_profile_fields_data`
		WHERE `user_id`=?");
# skenovat kazdou skupinu
$dbh->do("lock tables
	`phpbb_user_group` write,
	`evidence_clenstvi` write,
	`phpbb_groups` write,
	`phpbb_profile_fields` write,
	`phpbb_profile_fields_data` write,
	`phpbb_users` write,
	`evidence_log` write");
my ($den,$mes,$rok)=(localtime(time))[3,4,5];
$mes++;
$rok+=1900;
our $dnes=sprintf("%04d%02d%02d",$rok,$mes,$den);
foreach my $group (@groups)
	{
	# nejdriv pridat nove cleny
	my ($userid,$leader,$skupina);
	my $funkce=0;
	# najit cleny skupiny
	$sth1->execute($group) or die $sth1->errstr;
	$sth1->bind_columns(\($userid,$leader,$skupina));
	while ($sth1->fetch)
		{
		$funkce=0;
		if($skupina=~m/^KS\s/)
			{
			if($kstopks=~m/$group\=(\d+)/)
				{
				my $pks=$1;
				$sth1a->execute($userid,$pks) or die $sth1a->errstr;
				$funkce=1 if($sth1a->rows);
				$sth1a->finish;
				}
			}
		elsif($skupina=~m/^Repub.+bor$/ or $skupina=~m/^Repub.+tvo$/)
			{
			$sth1b->execute($userid,$group) or die $sth1b->errstr;
			$funkce=1 if($sth1b->rows);
			$sth1b->finish;
			}
		my $dat=$dnes;
		if($skupina=~m/^KS\s/ or $skupina=~m/^Repub.+bor$/ or $skupina=~m/^Repub.+tvo$/
		or $skupina=~m/^Celost/)
			{
			$sth7->execute($userid) or die $sth7->errstr;
			if($sth7->rows)
				{
				($dat)=$sth7->fetchrow_array();
				$dat=~s/\s+//g;
				if(length($dat))
					{
					$dat=~m/^(\d+).(\d+).(\d+)/;
					my ($d,$m,$r)=($1,$2,$3);
					$d=sprintf('%02d',$d);
					$m=sprintf('%02d',$m);
					$r=sprintf('%04d',$r);
					if($d > 0 and $m > 0 and $r > 0)
						{
						$dat="$r$m$d";
						}
					else
						{
						$dat=$dnes;
						}
					}
				else
					{
					$dat=$dnes;
					}
				}
			$sth7->finish;
			}
		# proverit clena, zda ma zapis v evidence_clenstvi
		$sth2->execute($userid,$group) or die $sth2->errstr;
		unless($sth2->rows)
			{
			#nema, tak zkusit clena s ukoncenym clenstvim
			$sth2a->execute($userid,$group) or die $sth2a->errstr;
			unless($sth2a->rows)
				{
				# ani ten tam neni, tak zapsat s dnesnim datumem
				$sth3->execute($userid,$group,$leader,$funkce,$dat) or die $sth3->errstr;
				$sth3->finish;
				my $t="GROUPLOG: doplněn člen '#' do skupiny '$skupina'\nVedoucí: "
					. ($leader ? 'ANO' : 'NE') . "\nFunkce: "
					. ($funkce ? 'ANO' : 'NE');
				&log_it(999999,$userid,$t);
				}
			$sth2a->finish;
			}
		else
			{
			# nacist
			my $row=$sth2->fetchrow_arrayref;
			if($userid==$row->[0] and ($leader!=$row->[1] or $funkce!=$row->[2]))
				{
				# uzivatel je leader, ale nema byt, nebo opacne
				# pripadne ma funkci, ale nema mit, nebo opacne
				# tak zapsat datum ukonceni
				$sth6->execute($userid,$group) or die $sth6->errstr;
				$sth6->finish;
				my $t="GROUPLOG: uzavřen předchozí stav pro člena '#' ve skupině '$skupina'\nVedoucí: ";
				if($leader!=$row->[1])
					{
					$t.=($leader ? 'ANO -> NE' : 'NE -> ANO');
					}
				else
					{
					$t.=($leader ? 'ANO -> ANO' : 'NE -> NE');
					}
				$t.="\nFunkce: ";
				if($funkce!=$row->[2])
					{
					$t.=($funkce ? 'ANO -> NE' : 'NE -> ANO');
					}
				else
					{
					$t.=($funkce ? 'ANO -> ANO' : 'NE -> NE');
					}
				&log_it(999999,$userid,$t);
				# a zapsat ho znovu spravne
				$sth3->execute($userid,$group,$leader,$funkce,$dat) or die $sth3->errstr;
				$sth3->finish;
				$t="GROUPLOG: zapsán nový stav pro člena '#' do skupiny '$skupina'\nVedoucí: "
					. ($leader ? 'ANO' : 'NE') . "\nFunkce: "
					. ($funkce ? 'ANO' : 'NE');
				&log_it(999999,$userid,$t);
				}
			}
		$sth2->finish;
		}
	$sth1->finish;
	# najit cleny v evidence_clenstvi, kteri jiz nejsou cleny skupiny
	$sth4->execute($group) or die $sth4->errstr;
	$sth4->bind_columns(\($userid,$leader,$funkce));
	while ($sth4->fetch)
		{
		$sth5->execute($userid,$group) or die $sth5->errstr;
		unless($sth5->rows)
			{
			# uzivatel jiz neni clenem skupiny
			# tak doplnit datum konce clenstvi do evidence_clenstvi
			$sth6->execute($userid,$group) or die $sth6->errstr;
			$sth6->finish;
			my $t="GROUPLOG: ukončeno členství člena '#' ve skupině '$skupina'";
			&log_it(999999,$userid,$t);
			}
		$sth5->finish;
		}
	$sth4->finish;
	}
$dbh->do("unlock tables");
$dbh->disconnect;
